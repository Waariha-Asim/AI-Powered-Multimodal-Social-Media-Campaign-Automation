
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import requests
import json
from datetime import datetime
import uvicorn

# ─── Config ──────────────────────────────────────────────────────────────────
DB_PATH         = "blogs.db"
CHROMA_DB_PATH  = "./chroma_db"
N8N_WEBHOOK_URL = "http://127.0.0.1:5678/webhook-test/blog-ingest"

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Social Media Campaign API",
    description="Backend for n8n + Streamlit social media pipeline",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database Setup ───────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS blogs (
        id              TEXT PRIMARY KEY,
        blog_text       TEXT,
        has_image       INTEGER DEFAULT 0,
        image_base64    TEXT,
        linkedin_post   TEXT,
        discord_post    TEXT,
        status          TEXT DEFAULT 'pending',
        quality_score   INTEGER DEFAULT 0,
        grounding_score INTEGER DEFAULT 0,
        claims_match    INTEGER DEFAULT 0,
        created_at      TIMESTAMP,
        published_at    TIMESTAMP,
        updated_at      TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (
        id          TEXT PRIMARY KEY,
        blog_id     TEXT,
        platform    TEXT,
        content     TEXT,
        status      TEXT,
        posted_at   TIMESTAMP,
        FOREIGN KEY (blog_id) REFERENCES blogs (id)
    )''')

    # ✅ Migration — existing DB ke liye
    try:
        c.execute("ALTER TABLE blogs ADD COLUMN has_image INTEGER DEFAULT 0")
    except:
        pass

    try:
        c.execute("ALTER TABLE blogs ADD COLUMN image_base64 TEXT DEFAULT ''")
    except:
        pass

    conn.commit()
    conn.close()

init_db()

# ─── Models ───────────────────────────────────────────────────────────────────
class BlogInput(BaseModel):
    blog_text:    str
    has_image:    bool = False
    image_base64: Optional[str] = ""

class N8NResultInput(BaseModel):
    blog_id:         str
    posts:           Optional[str] = ""      # raw JSON string from Gemini
    linkedin_post:   Optional[str] = ""      # parsed separately if available
    discord_post:    Optional[str] = ""      # parsed separately if available
    quality_score:   Optional[int] = 0
    grounding_score: Optional[int] = 0
    claims_match:    Optional[bool] = True
    status:          Optional[str] = "REVIEW"
    quality_status:  Optional[str] = "REVIEW"
    reason:          Optional[str] = ""

class ChromaQueryInput(BaseModel):
    blog_text: str
    n_results:  int = 3

class ChromaStoreInput(BaseModel):
    blog_id:   str
    blog_text: str

# ─── Helpers ──────────────────────────────────────────────────────────────────
def gen_id():
    return f"BLOG_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

def db():
    return sqlite3.connect(DB_PATH)

def parse_posts(posts_raw: str):
    """
    Parse raw Gemini output into linkedin_post and discord_post.
    Gemini returns a JSON string like:
    {"linkedin": "...", "discord": "..."}
    """
    linkedin_post = ""
    discord_post  = ""

    if not posts_raw:
        return linkedin_post, discord_post

    try:
        # Clean markdown fences if present
        cleaned = posts_raw.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        linkedin_post = data.get("linkedin", "")
        discord_post  = data.get("discord", "")
    except Exception as e:
        print(f"parse_posts error: {e} — raw: {posts_raw[:200]}")

    return linkedin_post, discord_post


def call_n8n(blog_id, blog_text, image_base64, has_image):
    payload = {
        "blog_id": blog_id,
        "blog_text": blog_text,
        "image_base64": image_base64,
        "has_image": has_image
    }

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        print(f"✅ n8n triggered for {blog_id}")
    except Exception as e:
        print(f"❌ n8n trigger failed: {e}")

# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "online", "service": "Social Media Campaign API"}


# 1. Streamlit sends blog → FastAPI stores it → triggers n8n webhook
@app.post("/api/store-blog")
async def store_blog(blog: BlogInput, background_tasks: BackgroundTasks):
    blog_id = gen_id()
    conn = db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO blogs (id, blog_text, has_image, image_base64, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (
        blog_id,
        blog.blog_text,
        int(blog.has_image),        # ✅ has_image save ho raha hai
        blog.image_base64 or "",
        datetime.now(),
        datetime.now()
    ))
    conn.commit()
    conn.close()

    background_tasks.add_task(
        call_n8n, blog_id, blog.blog_text, blog.image_base64 or "", blog.has_image
    )

    return {"blog_id": blog_id, "status": "pending", "message": "Blog stored, n8n triggered"}


# ─── FIX 1: /api/save-result ─────────────────────────────────────────────────
# Now parses linkedin_post + discord_post from raw posts string
# Now returns draft_id so Gmail email can use it
@app.post("/api/save-result")
async def save_result(data: N8NResultInput):
    """
    n8n posts generated posts + scores here.
    Parses raw Gemini JSON into linkedin_post + discord_post.
    Returns draft_id = blog_id for approval flow.
    """
    # Parse posts if raw string provided and individual fields are empty
    linkedin_post = data.linkedin_post or ""
    discord_post  = data.discord_post or ""

    if (not linkedin_post or not discord_post) and data.posts:
        linkedin_post, discord_post = parse_posts(data.posts)

    # Use quality_status if status is raw Groq status (PASS/REVIEW/BLOCK)
    final_status = data.quality_status or data.status or "REVIEW"

    conn = db()
    c = conn.cursor()
    c.execute("""
        UPDATE blogs
        SET linkedin_post   = ?,
            discord_post    = ?,
            quality_score   = ?,
            grounding_score = ?,
            claims_match    = ?,
            status          = ?,
            updated_at      = ?
        WHERE id = ?
    """, (
        linkedin_post,
        discord_post,
        data.quality_score,
        data.grounding_score,
        int(data.claims_match),
        final_status,
        datetime.now(),
        data.blog_id
    ))
    conn.commit()
    conn.close()

    # ✅ draft_id returned — Gmail email uses this
    return {
        "success":      True,
        "blog_id":      data.blog_id,
        "draft_id":     data.blog_id,   # draft_id = blog_id in this system
        "status":       final_status,
        "linkedin_post": linkedin_post,
        "discord_post":  discord_post
    }


# 3. Fetch blog by ID — used by n8n Fetch Blog node
@app.get("/api/blog/{blog_id}")
async def get_blog(blog_id: str):
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT id, blog_text, image_base64, linkedin_post, discord_post,
               status, quality_score, grounding_score, claims_match,
               created_at, updated_at
        FROM blogs WHERE id = ?
    """, (blog_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Blog not found")

    image_base64 = row[2] or ""

    return {
        "blog_id":         row[0],
        "blog_text":       row[1],
        "image_base64":    image_base64,
        "has_image":       bool(image_base64),
        "linkedin_post":   row[3] or "",
        "discord_post":    row[4] or "",
        "status":          row[5],
        "quality_score":   row[6] or 0,
        "grounding_score": row[7] or 0,
        "claims_match":    bool(row[8]),
        "created_at":      str(row[9]),
        "updated_at":      str(row[10])
    }


# ─── FIX 2: /api/draft/{draft_id} ────────────────────────────────────────────
# This was MISSING — caused 404 in Workflow 2 Fetch Approved Draft node
@app.get("/api/draft/{draft_id}")
async def get_draft(draft_id: str):
    """
    Workflow 2 calls this after approval click.
    draft_id = blog_id in this system.
    Returns linkedin_post + discord_post + image fields for publishing.
    """
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT id, blog_text, linkedin_post, discord_post,
               status, quality_score, grounding_score, claims_match,
               image_base64, has_image
        FROM blogs WHERE id = ?
    """, (draft_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Draft not found")

    image_base64 = row[8] or ""
    has_image    = bool(row[9]) or bool(image_base64)

    return {
        "draft_id":        row[0],
        "blog_id":         row[0],
        "blog_text":       row[1],
        "linkedin_post":   row[2] or "",
        "discord_post":    row[3] or "",
        "status":          row[4],
        "quality_score":   row[5] or 0,
        "grounding_score": row[6] or 0,
        "claims_match":    bool(row[7]),
        "image_base64":    image_base64,      # ✅ ab return ho raha hai
        "has_image":       has_image          # ✅ ab return ho raha hai
    }

# ─── FIX 3: /api/draft/{draft_id}/reject ─────────────────────────────────────
@app.post("/api/draft/{draft_id}/reject")
async def reject_draft(draft_id: str):
    """Workflow 2 reject branch calls this"""
    conn = db()
    c = conn.cursor()
    c.execute("""
        UPDATE blogs SET status = 'rejected', updated_at = ? WHERE id = ?
    """, (datetime.now(), draft_id))
    conn.commit()
    conn.close()
    return {"draft_id": draft_id, "status": "rejected"}


# 4. Approve via old route (Streamlit button)
@app.post("/api/blog/{blog_id}/approve")
async def approve_blog(blog_id: str, background_tasks: BackgroundTasks):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT linkedin_post, discord_post FROM blogs WHERE id = ?", (blog_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Blog not found")

    c.execute("""
        UPDATE blogs SET status = 'approved', updated_at = ? WHERE id = ?
    """, (datetime.now(), blog_id))
    conn.commit()
    conn.close()

    return {"blog_id": blog_id, "status": "approved"}


# 5. Reject via old route (Streamlit button)
@app.post("/api/blog/{blog_id}/reject")
async def reject_blog(blog_id: str):
    conn = db()
    c = conn.cursor()
    c.execute("""
        UPDATE blogs SET status = 'rejected', updated_at = ? WHERE id = ?
    """, (datetime.now(), blog_id))
    conn.commit()
    conn.close()
    return {"blog_id": blog_id, "status": "rejected"}


# 6. History for Streamlit tab
@app.get("/api/history")
async def get_history(limit: int = 20):
    conn = db()
    c = conn.cursor()
    c.execute("""
        SELECT id, status, quality_score, linkedin_post,
               discord_post, created_at
        FROM blogs ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()

    return [{
        "blog_id":         r[0],
        "linkedin_status": r[1] or "pending",
        "discord_status":  r[1] or "pending",
        "quality_score":   r[2] or 0,
        "published_at":    str(r[5]) if r[5] else "",
        "preview":         (r[3] or r[4] or "")[:150]
    } for r in rows]


# 7. Stats for Streamlit header
@app.get("/api/stats")
async def get_stats():
    conn = db()
    c = conn.cursor()
    counts = {}
    for status in ["pending", "approved", "rejected", "PASS", "REVIEW", "BLOCK"]:
        c.execute("SELECT COUNT(*) FROM blogs WHERE status = ?", (status,))
        counts[status] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM blogs")
    counts["total"] = c.fetchone()[0]
    conn.close()
    return {
        "total":     counts["total"],
        "published": counts["approved"],
        "pending":   counts["pending"] + counts["REVIEW"] + counts["PASS"],
        "blocked":   counts["BLOCK"] + counts["rejected"]
    }


# 8. ChromaDB query — n8n calls this for brand memory
@app.post("/api/chromadb/query")
async def query_chromadb(data: ChromaQueryInput):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        try:
            col = client.get_collection("brand_memory")
        except Exception:
            return {"brand_context": "", "matches": [], "message": "No brand memory yet"}

        results = col.query(
            query_texts=[data.blog_text[:1000]],
            n_results=min(data.n_results, max(col.count(), 1))
        )
        docs = results.get("documents", [[]])[0]
        return {
            "brand_context": "\n\n".join(docs),
            "matches":       docs,
            "message":       f"Found {len(docs)} matches"
        }
    except ImportError:
        return {"brand_context": "", "matches": [], "message": "pip install chromadb"}
    except Exception as e:
        return {"brand_context": "", "matches": [], "message": str(e)}


# 9. ChromaDB store
@app.post("/api/chromadb/store")
async def store_chromadb(data: ChromaStoreInput):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        col = client.get_or_create_collection("brand_memory")
        col.upsert(documents=[data.blog_text[:2000]], ids=[data.blog_id])
        return {"success": True, "blog_id": data.blog_id}
    except ImportError:
        return {"success": False, "message": "pip install chromadb"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 FastAPI running → http://127.0.0.1:8000")
    print("📖 API Docs      → http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")