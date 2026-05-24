"""
app.py — TechVoice Publisher — Streamlit multi-page entry point.
"""
import sys
import os
import logging

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="تيك فويس — ناشر المحتوى",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "أداة نشر محتوى تيك فويس على منصات التواصل الاجتماعي",
    },
)

# ── Global RTL + Dark theme styles ───────────────────────────────────────────
st.markdown(
    """
    <style>
        /* Global RTL */
        body, .main, .block-container, .stApp {
            direction: rtl;
            text-align: right;
        }

        /* Fix Streamlit elements that need LTR */
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox select,
        .stNumberInput input {
            direction: ltr;
            text-align: left;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            direction: rtl;
        }

        /* Table cells */
        td, th {
            direction: rtl;
            text-align: right !important;
        }

        /* Button alignment */
        .stButton > button {
            direction: rtl;
        }

        /* Dark card style */
        .tv-card {
            background: #1e1e2e;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
            border: 1px solid #333;
        }

        /* Divider color */
        hr {
            border-color: #333;
        }

        /* Hide Streamlit branding */
        #MainMenu, footer, header { visibility: hidden; }

        /* Expander */
        .streamlit-expanderHeader {
            direction: rtl;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Initialize database on first run ─────────────────────────────────────────
@st.cache_resource
def _init():
    try:
        from core.database import init_db
        init_db()
        logger.info("Database ready")
    except Exception as e:
        logger.error("DB init failed: %s", e)

    try:
        from core.scheduler import start_scheduler
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.error("Scheduler start failed: %s", e)

    return True


_init()

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:16px 0;">
            <div style="font-size:40px;">🎬</div>
            <div style="font-size:18px;font-weight:bold;color:#fff;">تيك فويس</div>
            <div style="font-size:12px;color:#aaa;">ناشر المحتوى</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    PAGES = {
        "📊 لوحة التحكم": "dashboard",
        "⚙️ الإعدادات": "settings",
    }

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "dashboard"

    for label, page_key in PAGES.items():
        is_active = st.session_state["current_page"] == page_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(label, key=f"nav_{page_key}", use_container_width=True, type=btn_type):
            st.session_state["current_page"] = page_key
            st.rerun()

    st.divider()

    # Status indicators
    from core.config import is_configured
    from core.scheduler import is_running
    from core.database import get_all_tasks

    notion_ok = is_configured()
    sched_ok = is_running()
    tasks = get_all_tasks()
    pending_count = sum(1 for t in tasks if t["status"] in ("pending", "scheduled"))

    st.markdown(
        f"""
        <div style="font-size:12px;color:#aaa;">
            <div>{'✅' if notion_ok else '❌'} Notion: {'متصل' if notion_ok else 'غير مُعدّ'}</div>
            <div>{'✅' if sched_ok else '⏸'} المُجدوِل: {'يعمل' if sched_ok else 'متوقف'}</div>
            <div>📋 مهام معلّقة: {pending_count}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Page routing ──────────────────────────────────────────────────────────────
current = st.session_state.get("current_page", "dashboard")

if current == "dashboard":
    from ui.dashboard import show
    show()

elif current == "settings":
    from ui.settings import show
    show()
