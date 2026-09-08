import streamlit as st
import requests
import json
import base64
from datetime import datetime
import time

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Social Media Campaign Automation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Configuration ─────────────────────────────────────────────────────────
FASTAPI_URL = "http://127.0.0.1:8000"
N8N_WEBHOOK_URL = "http://127.0.0.1:5678/webhook-test/blog-ingest"

# ─── Session State ─────────────────────────────────────────────────────────
if "generated_posts" not in st.session_state:
    st.session_state.generated_posts = None
if "workflow_status" not in st.session_state:
    st.session_state.workflow_status = None
if "blog_id" not in st.session_state:
    st.session_state.blog_id = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# ─── CSS Styling ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: #000000;
    color: #e2e8f0;
}

.stApp {
    background: radial-gradient(ellipse at 20% 10%, #1a0533 0%, #000000 50%, #000d1a 100%);
    min-height: 100vh;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.top-header {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 32px;
    backdrop-filter: blur(20px);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.header-left h1 {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 4px 0;
    letter-spacing: -0.3px;
}

.header-left p {
    font-size: 13px;
    color: #64748b;
    margin: 0;
}

.header-badge {
    background: rgba(124, 58, 237, 0.15);
    border: 1px solid rgba(124, 58, 237, 0.3);
    color: #a78bfa;
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 20px;
}

.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 20px;
    backdrop-filter: blur(16px);
    transition: border-color 0.2s ease;
}

.glass-card:hover {
    border-color: rgba(124, 58, 237, 0.25);
}

.card-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: #7c3aed;
    margin-bottom: 12px;
}

.card-title {
    font-size: 16px;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 4px;
}

.card-sub {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 20px;
}

.stat-row {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
}

.stat-card {
    flex: 1;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 20px 24px;
    backdrop-filter: blur(12px);
}

.stat-value {
    font-size: 28px;
    font-weight: 700;
    color: #a78bfa;
    line-height: 1;
    margin-bottom: 6px;
}

.stat-label {
    font-size: 12px;
    color: #64748b;
    font-weight: 500;
}

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.badge-pass {
    background: rgba(34, 197, 94, 0.12);
    border: 1px solid rgba(34, 197, 94, 0.25);
    color: #22c55e;
}

.badge-review {
    background: rgba(234, 179, 8, 0.12);
    border: 1px solid rgba(234, 179, 8, 0.25);
    color: #eab308;
}

.badge-block {
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.25);
    color: #ef4444;
}

.badge-published {
    background: rgba(124, 58, 237, 0.12);
    border: 1px solid rgba(124, 58, 237, 0.25);
    color: #a78bfa;
}

.badge-rejected {
    background: rgba(100, 116, 139, 0.12);
    border: 1px solid rgba(100, 116, 139, 0.25);
    color: #64748b;
}

.platform-row {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

.platform-chip {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 6px;
}

.post-preview {
    background: rgba(0,0,0,0.4);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 14px;
    font-size: 13px;
    line-height: 1.7;
    color: #cbd5e1;
    white-space: pre-wrap;
}

.post-platform-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.label-linkedin { color: #60a5fa; }
.label-discord  { color: #a78bfa; }

.progress-track {
    background: rgba(255,255,255,0.06);
    border-radius: 99px;
    height: 6px;
    margin-top: 8px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #7c3aed, #a78bfa);
    transition: width 0.4s ease;
}

.history-row {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.history-meta {
    font-size: 12px;
    color: #475569;
    margin-top: 2px;
}

.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    resize: vertical !important;
}

.stTextArea textarea:focus {
    border-color: rgba(124, 58, 237, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1) !important;
}

.stTextArea label, .stFileUploader label, .stSelectbox label {
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 12px 28px !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.2px !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #6d28d9 0%, #5b21b6 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(124, 58, 237, 0.35) !important;
}

.stButton > button[kind="secondary"] {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}

.stButton > button[kind="secondary"]:hover {
    border-color: rgba(124, 58, 237, 0.4) !important;
    color: #a78bfa !important;
}

.stFileUploader {
    background: rgba(255,255,255,0.03) !important;
    border: 1px dashed rgba(255,255,255,0.1) !important;
    border-radius: 12px !important;
    padding: 8px !important;
}

.stSelectbox > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

.stAlert {
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
}

hr {
    border-color: rgba(255,255,255,0.06) !important;
    margin: 24px 0 !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    gap: 2px !important;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #64748b !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
}

.stTabs [aria-selected="true"] {
    background: rgba(124, 58, 237, 0.2) !important;
    color: #a78bfa !important;
}

.stSpinner > div {
    border-top-color: #7c3aed !important;
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(124,58,237,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(124,58,237,0.5); }

.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
}
.status-dot.online { background: #22c55e; }
.status-dot.offline { background: #ef4444; }
.status-dot.processing { background: #eab308; animation: pulse 1.5s infinite; }

@keyframes pulse {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
    100% { opacity: 1; transform: scale(1); }
}
</style>
""", unsafe_allow_html=True)

# ─── Helper Functions ──────────────────────────────────────────────────────

def check_api_status():
    """Check if FastAPI server is running"""
    try:
        response = requests.get(f"{FASTAPI_URL}/", timeout=3)
        return response.status_code == 200
    except:
        return False

def fetch_stats():
    """Fetch statistics from FastAPI"""
    try:
        response = requests.get(f"{FASTAPI_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {"total": 0, "published": 0, "pending": 0, "blocked": 0}

def fetch_history():
    """Fetch blog history from FastAPI"""
    try:
        response = requests.get(f"{FASTAPI_URL}/api/history", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def process_blog_sync(blog_text: str, image_b64: str | None):
    """Process blog synchronously through FastAPI"""
    try:
        payload = {
            "blog_text": blog_text,
            "has_image": image_b64 is not None,
            "image_base64": image_b64 or ""
        }
        response = requests.post(
            f"{FASTAPI_URL}/api/store-blog",
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"API Error: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return False, {"error": f"Cannot connect to FastAPI at {FASTAPI_URL}"}
    except Exception as e:
        return False, {"error": str(e)}

def trigger_workflow(blog_text: str, image_b64: str | None):
    """Trigger n8n workflow"""
    try:
        payload = {
            "blog_text": blog_text,
            "has_image": image_b64 is not None,
            "image_base64": image_b64 or ""
        }
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
        if response.status_code == 200:
            return True, response.json() if response.text else {}
        return False, {"error": f"n8n returned {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

# ─── Header ────────────────────────────────────────────────────────────────

api_status = check_api_status()

st.markdown(f"""
<div class="top-header">
    <div class="header-left">
        <h1>⚡ Social Media Campaign Automation</h1>
        <p>AI-Powered Multimodal Content Generation & Publishing Automation</p>
    </div>
    <div style="display:flex; gap:15px; align-items:center;">
        <div class="platform-chip">🔵 LinkedIn</div>
        <div class="platform-chip">🟣 Discord</div>
        <span class="header-badge">
            <span class="status-dot {'online' if api_status else 'offline'}"></span>
            {'API Online' if api_status else 'API Offline'}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Stats Row ─────────────────────────────────────────────────────────────

stats = fetch_stats()
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats.get('total', 0)}</div>
        <div class="stat-label">Total Campaigns</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value" style="color:#22c55e;">{stats.get('published', 0)}</div>
        <div class="stat-label">Published</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value" style="color:#eab308;">{stats.get('pending', 0)}</div>
        <div class="stat-label">Awaiting Approval</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value" style="color:#ef4444;">{stats.get('blocked', 0)}</div>
        <div class="stat-label">Blocked</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Tabs ──────────────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["  Generate Campaign  ", "  Publish History  "])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — GENERATE
# ════════════════════════════════════════════════════════════════════════════

with tab1:
    col_left, col_right = st.columns([1.1, 0.9], gap="large")

    # ── LEFT: Input ─────────────────────────────────────────────────────────
    with col_left:
        st.markdown("""
        <div class="glass-card">
            <div class="card-label">Input</div>
            <div class="card-title">Blog Content</div>
            <div class="card-sub">Paste your blog post or article below</div>
        </div>
        """, unsafe_allow_html=True)

        blog_text = st.text_area(
            "Blog Text",
            placeholder="Paste your full blog post or article here...\n\nThe system will generate platform-specific posts for LinkedIn and Discord, run multimodal validation, grounding checks, and quality scoring before sending for your approval.",
            height=280,
            label_visibility="collapsed"
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <div class="glass-card">
            <div class="card-label">Multimodal</div>
            <div class="card-title">Upload Image <span style="color:#475569; font-weight:400; font-size:13px;">(Optional)</span></div>
            <div class="card-sub">Groq vision AI will check if the image matches your blog topic</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload Image",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed"
        )

        image_b64 = None
        if uploaded_file:
            image_bytes = uploaded_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            st.image(uploaded_file, caption="", use_container_width=True)
            st.markdown("""
            <div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.2); border-radius:8px; padding:10px 14px; font-size:12px; color:#22c55e; margin-top:8px;">
                ✓ Image ready — Groq will validate relevance
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Model info strip
        st.markdown("""
        <div style="background:rgba(124,58,237,0.06); border:1px solid rgba(124,58,237,0.15); border-radius:10px; padding:14px 18px; margin-bottom:20px;">
            <div style="font-size:11px; font-weight:600; letter-spacing:1px; color:#7c3aed; margin-bottom:10px;">AI PIPELINE</div>
            <div style="display:flex; flex-direction:column; gap:6px;">
                <div style="font-size:12px; color:#94a3b8; display:flex; justify-content:space-between;">
                    <span>📝 Content Generation</span><span style="color:#a78bfa;">Gemini 2.0 Flash</span>
                </div>
                <div style="font-size:12px; color:#94a3b8; display:flex; justify-content:space-between;">
                    <span>🖼️ Image Validation</span><span style="color:#a78bfa;">Groq Vision</span>
                </div>
                <div style="font-size:12px; color:#94a3b8; display:flex; justify-content:space-between;">
                    <span>✅ Quality Scoring</span><span style="color:#a78bfa;">Multi-factor</span>
                </div>
                <div style="font-size:12px; color:#94a3b8; display:flex; justify-content:space-between;">
                    <span>📧 Approval Flow</span><span style="color:#a78bfa;">Email + Dashboard</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Buttons row - single full width button
        if st.button("⚡ Generate Campaign", type="primary", use_container_width=True):
            if not blog_text.strip():
                st.error("Please paste your blog content first.")
            elif not api_status:
                st.error(f"FastAPI server not running at {FASTAPI_URL}")
            else:
                with st.spinner("Processing through AI pipeline..."):
                    st.session_state.processing = True
                    success, result = process_blog_sync(blog_text, image_b64)
                    st.session_state.processing = False

                    if success:
                        st.session_state.workflow_status = "triggered"
                        st.session_state.generated_posts = result
                        st.session_state.blog_id = result.get("blog_id")
                        st.success(f"✓ Campaign generated! ID: {result.get('blog_id')}")
                        st.rerun()
                    else:
                        st.error(f"Error: {result.get('error', 'Unknown error')}")


    # ── RIGHT: Output Preview ──────────────────────────────────────────────
    with col_right:
        st.markdown("""
        <div class="glass-card">
            <div class="card-label">Output</div>
            <div class="card-title">Generated Posts Preview</div>
            <div class="card-sub">Posts appear here after processing</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.generated_posts and st.session_state.workflow_status == "triggered":
            data = st.session_state.generated_posts

            # Quality score
            quality = data.get("quality_score", 0)
            status = data.get("status", "REVIEW")
            badge_class = {
                "PASS": "badge-pass",
                "REVIEW": "badge-review",
                "BLOCK": "badge-block",
                "published": "badge-published",
                "rejected": "badge-rejected"
            }.get(status, "badge-review")

            st.markdown(f"""
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
                <span style="font-size:13px; color:#64748b;">Quality Score</span>
                <span class="badge {badge_class}">{status}</span>
            </div>
            <div style="font-size:32px; font-weight:700; color:#a78bfa; margin-bottom:6px;">{quality}<span style="font-size:16px; color:#475569;">/100</span></div>
            <div class="progress-track"><div class="progress-fill" style="width:{quality}%;"></div></div>
            <hr/>
            """, unsafe_allow_html=True)

            # LinkedIn post
            linkedin_post = data.get("linkedin_post", data.get("posts", {}).get("linkedin", ""))
            if linkedin_post:
                st.markdown("""<div class="post-platform-label label-linkedin">🔵 LinkedIn Post</div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="post-preview">{linkedin_post}</div>""", unsafe_allow_html=True)

            # Discord post
            discord_post = data.get("discord_post", data.get("posts", {}).get("discord", ""))
            if discord_post:
                st.markdown("""<div class="post-platform-label label-discord">🟣 Discord Post</div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="post-preview">{discord_post}</div>""", unsafe_allow_html=True)

            # Grounding info
            grounding = data.get("grounding_score", "—")
            claims = data.get("claims_match", True)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:14px 16px; margin-top:8px;">
                <div style="font-size:11px; font-weight:600; letter-spacing:1px; color:#475569; margin-bottom:10px;">VALIDATION DETAILS</div>
                <div style="display:flex; justify-content:space-between; font-size:12px; color:#94a3b8; margin-bottom:6px;">
                    <span>Grounding Score</span><span style="color:#a78bfa;">{grounding}/100</span>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:12px; color:#94a3b8;">
                    <span>Claims Verified</span><span style="color:{'#22c55e' if claims else '#ef4444'};">{'✓ Yes' if claims else '✗ Issues found'}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Actions
            if st.session_state.blog_id:
                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    if st.button("✅ Approve & Publish", key="approve_btn"):
                        try:
                            response = requests.post(f"{FASTAPI_URL}/api/blog/{st.session_state.blog_id}/approve")
                            if response.status_code == 200:
                                st.success("✅ Blog approved and published!")
                                st.rerun()
                            else:
                                st.error("Failed to approve")
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col_act2:
                    if st.button("❌ Reject", key="reject_btn"):
                        try:
                            response = requests.post(f"{FASTAPI_URL}/api/blog/{st.session_state.blog_id}/reject")
                            if response.status_code == 200:
                                st.warning("❌ Blog rejected")
                                st.rerun()
                            else:
                                st.error("Failed to reject")
                        except Exception as e:
                            st.error(f"Error: {e}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div style="background:rgba(124,58,237,0.06); border:1px solid rgba(124,58,237,0.15); border-radius:10px; padding:14px 16px; font-size:13px; color:#a78bfa; text-align:center;">
                📧 Approval email sent — check your Gmail to approve or reject
            </div>
            """, unsafe_allow_html=True)

        else:
            # Empty state
            st.markdown("""
            <div style="text-align:center; padding: 60px 20px; color:#334155;">
                <div style="font-size:40px; margin-bottom:16px; opacity:0.4;">⚡</div>
                <div style="font-size:15px; font-weight:500; color:#475569; margin-bottom:8px;">No campaign generated yet</div>
                <div style="font-size:13px; color:#334155; line-height:1.6;">
                    Paste your blog content and click<br/>Generate to start the pipeline
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Pipeline steps visual
            st.markdown("<hr>", unsafe_allow_html=True)
            steps = [
                ("01", "Blog Ingestion", "Stored in SQLite via FastAPI"),
                ("02", "AI Generation", "Gemini 2.0 Flash creates posts"),
                ("03", "Vision Check", "Groq validates image relevance"),
                ("04", "Quality Gate", "Multi-factor quality scoring"),
                ("05", "Approval Flow", "You approve or reject"),
                ("06", "Auto Publish", "LinkedIn + Discord go live"),
            ]
            for num, title, desc in steps:
                st.markdown(f"""
                <div style="display:flex; align-items:flex-start; gap:14px; margin-bottom:14px;">
                    <div style="min-width:28px; height:28px; background:rgba(124,58,237,0.15); border:1px solid rgba(124,58,237,0.25); border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; color:#7c3aed;">{num}</div>
                    <div>
                        <div style="font-size:13px; font-weight:600; color:#cbd5e1;">{title}</div>
                        <div style="font-size:12px; color:#475569;">{desc}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    col_h1, col_h2 = st.columns([3, 1])

    with col_h1:
        st.markdown("""
        <div class="glass-card">
            <div class="card-label">Records</div>
            <div class="card-title">Publish History</div>
            <div class="card-sub">All campaigns — published, rejected, and blocked</div>
        </div>
        """, unsafe_allow_html=True)

    with col_h2:
        filter_status = st.selectbox(
            "Filter",
            ["All", "published", "rejected", "blocked", "pending", "PASS", "REVIEW", "BLOCK"],
            label_visibility="collapsed"
        )

    if st.button("🔄 Refresh History", use_container_width=True):
        st.rerun()

    history = fetch_history()

    if filter_status != "All":
        history = [h for h in history if h.get("linkedin_status") == filter_status]

    if not history:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:#334155;">
            <div style="font-size:13px; color:#475569;">No records found</div>
            <div style="font-size:12px; color:#334155; margin-top:8px;">Generate a campaign to see it here</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for item in history:
            status = item.get("linkedin_status", "unknown")
            badge_class = {
                "published": "badge-published",
                "rejected": "badge-rejected",
                "blocked": "badge-block",
                "PASS": "badge-pass",
                "REVIEW": "badge-review",
                "BLOCK": "badge-block",
                "pending": "badge-review"
            }.get(status, "badge-review")

            score = item.get("quality_score", 0)
            blog_id = item.get("blog_id", "—")
            ts = item.get("published_at", "")
            preview = item.get("preview", "No preview available")

            try:
                if ts:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_display = dt.strftime("%b %d, %Y · %I:%M %p")
                else:
                    ts_display = "Not published yet"
            except Exception:
                ts_display = ts

            col_info, col_badge, col_score = st.columns([4, 1.2, 1])

            with col_info:
                st.markdown(f"""
                <div class="glass-card" style="margin-bottom:0; padding:16px 20px;">
                    <div style="font-size:13px; color:#f1f5f9; font-weight:500; margin-bottom:4px;">Blog #{blog_id}</div>
                    <div style="font-size:12px; color:#64748b; margin-bottom:6px;">{ts_display}</div>
                    <div style="font-size:12px; color:#475569; line-height:1.5;">{preview[:120]}{"..." if len(preview) > 120 else ""}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_badge:
                st.markdown(f"""
                <div style="padding-top:28px; text-align:center;">
                    <span class="badge {badge_class}">{status.upper()}</span>
                </div>
                """, unsafe_allow_html=True)

            with col_score:
                score_color = "#22c55e" if score >= 75 else "#eab308" if score >= 50 else "#ef4444"
                st.markdown(f"""
                <div style="padding-top:20px; text-align:center;">
                    <div style="font-size:22px; font-weight:700; color:{score_color};">{score}</div>
                    <div style="font-size:11px; color:#475569;">quality</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)