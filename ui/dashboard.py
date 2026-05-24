"""
dashboard.py — لوحة التحكم: قائمة المهام + عرض كانبان + نشر/جدولة.
"""
import streamlit as st
from datetime import datetime
from typing import List, Dict, Any, Optional


# ── ثوابت ─────────────────────────────────────────────────────────────────────

PLATFORM_COLORS = {
    "tiktok":    ("#ff2d55", "🎵"),
    "youtube":   ("#FF0000", "▶️"),
    "instagram": ("#C13584", "📸"),
    "x":         ("#1DA1F2", "✖️"),
}

STATUS_META = {
    "pending":    ("#FFA500", "⏳", "بانتظار النشر"),
    "scheduled":  ("#3399FF", "📅", "مجدول"),
    "publishing": ("#9966FF", "🔄", "جارٍ النشر"),
    "done":       ("#00CC66", "✅", "تم النشر"),
    "failed":     ("#FF4444", "❌", "فشل"),
}


def _plat_badges(platforms: List[str]) -> str:
    parts = []
    for p in platforms:
        color, icon = PLATFORM_COLORS.get(p, ("#666", "•"))
        parts.append(
            f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
            f'padding:2px 7px;border-radius:4px;font-size:11px;margin-left:3px;">'
            f'{icon} {p.upper()}</span>'
        )
    return "".join(parts)


def _status_chip(status: str) -> str:
    color, icon, label = STATUS_META.get(status, ("#888", "•", status))
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
        f'padding:3px 10px;border-radius:10px;font-size:12px;">{icon} {label}</span>'
    )


def _fmt_dt(iso: Optional[str]) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y  %H:%M")
    except Exception:
        return iso


# ══════════════════════════════════════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════════════════════════════════════

def show():
    from core.database import get_all_tasks
    from core.config import is_configured
    from core.scheduler import start_scheduler, is_running

    st.markdown(
        '<h1 style="direction:rtl;">🎬 لوحة التحكم</h1>',
        unsafe_allow_html=True,
    )

    if not is_running():
        try:
            start_scheduler()
        except Exception:
            pass

    if not is_configured():
        st.warning("⚠️ أعدّ توكن Notion وقاعدة البيانات في ⚙️ الإعدادات أولاً.")
        return

    # ── شريط الأوامر ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([2, 2, 1, 3])

    with c1:
        if st.button("📥 اسحب المهام من Notion", use_container_width=True):
            _pull_from_notion()

    with c2:
        if st.button("🚀 نشر الجاهز الآن", use_container_width=True, type="primary"):
            _publish_all_pending()

    with c3:
        view = st.selectbox(
            "عرض", ["📋 قائمة", "🗂️ كانبان"],
            label_visibility="collapsed",
            key="dash_view",
        )

    tasks = get_all_tasks()

    with c4:
        total   = len(tasks)
        pending = sum(1 for t in tasks if t["status"] in ("pending", "scheduled"))
        done    = sum(1 for t in tasks if t["status"] == "done")
        failed  = sum(1 for t in tasks if t["status"] == "failed")
        st.markdown(
            f'<div style="direction:rtl;padding-top:8px;font-size:13px;color:#aaa;">'
            f'الكل: <b style="color:#fff;">{total}</b> &nbsp;|&nbsp; '
            f'جاهز: <b style="color:#FFA500;">{pending}</b> &nbsp;|&nbsp; '
            f'منشور: <b style="color:#00CC66;">{done}</b> &nbsp;|&nbsp; '
            f'فشل: <b style="color:#FF4444;">{failed}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    if not tasks:
        st.info("لا توجد مهام. اضغط «اسحب المهام من Notion» لجلب المحتوى الجاهز.", icon="📋")
    else:
        if view == "📋 قائمة":
            _list_view(tasks)
        else:
            _kanban_view(tasks)

    # ── سجل النشر ─────────────────────────────────────────────────────────────
    st.divider()
    with st.expander("📋 سجل النشر الأخير", expanded=False):
        _post_history()


# ══════════════════════════════════════════════════════════════════════════════
# عرض القائمة
# ══════════════════════════════════════════════════════════════════════════════

def _list_view(tasks: List[Dict]):
    f_col, _ = st.columns([2, 5])
    with f_col:
        status_filter = st.selectbox(
            "فلتر",
            ["الكل", "⏳ بانتظار النشر", "📅 مجدول", "✅ تم النشر", "❌ فشل"],
            label_visibility="collapsed",
            key="list_filter",
        )

    key_map = {
        "⏳ بانتظار النشر": "pending",
        "📅 مجدول":        "scheduled",
        "✅ تم النشر":     "done",
        "❌ فشل":          "failed",
    }
    fk = key_map.get(status_filter)
    shown = tasks if not fk else [t for t in tasks if t["status"] == fk]

    for task in shown:
        _render_list_card(task)


def _render_list_card(task: Dict):
    from core.database import delete_task
    from core.scheduler import run_task_now, schedule_task

    status = task.get("status", "pending")
    _, _, status_label = STATUS_META.get(status, ("#888", "•", status))
    color, _, _ = STATUS_META.get(status, ("#888", "•", status))

    name    = task.get("name") or "—"
    caption = (task.get("caption") or "").strip()
    caption_preview = (caption[:80] + "…") if len(caption) > 80 else caption

    with st.container():
        # ── Header: اسم + حالة ──────────────────────────────────────────
        st.markdown(
            f'<div style="background:#1e1e2e;border-radius:10px;'
            f'border-right:4px solid {color};padding:14px 16px 10px 16px;'
            f'margin-bottom:4px;direction:rtl;">'

            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;">'
            f'<strong style="font-size:16px;color:#fff;">{name}</strong>'
            f'{_status_chip(status)}'
            f'</div>'

            + (f'<div style="color:#bbb;font-size:13px;margin-top:6px;">{caption_preview}</div>'
               if caption_preview else "")

            + f'<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;">'
            f'{_plat_badges(task.get("platforms", []))}'
            f'</div>'

            f'<div style="margin-top:8px;color:#666;font-size:12px;display:flex;gap:16px;flex-wrap:wrap;">'
            f'<span>🕐 {_fmt_dt(task.get("scheduled_at"))}</span>'
            f'<span>📁 {task.get("content_type", "video")}</span>'
            f'</div>'

            + (f'<div style="color:#FF6666;font-size:12px;margin-top:6px;">❌ {task["error_msg"][:120]}</div>'
               if task.get("error_msg") else "")

            + f'</div>',
            unsafe_allow_html=True,
        )

        # ── أزرار التحكم ────────────────────────────────────────────────
        ca, cb, cc = st.columns([2, 3, 1])

        with ca:
            if status in ("pending", "scheduled", "failed"):
                if st.button("▶️ نشر الآن", key=f"now_{task['id']}", use_container_width=True):
                    with st.spinner("جارٍ النشر… قد يستغرق دقيقة"):
                        run_task_now(task["id"])
                    st.session_state[f"_publish_result_{task['id']}"] = True
                    st.rerun()

        # عرض نتيجة النشر بعد العملية
        result_key = f"_publish_result_{task['id']}"
        if st.session_state.get(result_key):
            _show_publish_result(task["id"])
            del st.session_state[result_key]

        with cb:
            if status in ("pending", "failed"):
                sc1, sc2, sc3 = st.columns([2, 2, 1])
                with sc1:
                    sched_date = st.date_input("", key=f"date_{task['id']}",
                                               label_visibility="collapsed")
                with sc2:
                    sched_time = st.time_input("", key=f"time_{task['id']}",
                                               label_visibility="collapsed")
                with sc3:
                    if st.button("📅", key=f"sched_{task['id']}", help="جدولة",
                                 use_container_width=True):
                        run_at = datetime.combine(sched_date, sched_time)
                        schedule_task(task["id"], run_at)
                        st.rerun()

        with cc:
            if st.button("🗑️", key=f"del_{task['id']}", help="حذف"):
                delete_task(task["id"])
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# عرض كانبان
# ══════════════════════════════════════════════════════════════════════════════

def _kanban_view(tasks: List[Dict]):
    columns_def = [
        ("pending",   "⏳ بانتظار النشر", "#FFA500"),
        ("scheduled", "📅 مجدول",        "#3399FF"),
        ("done",      "✅ تم النشر",     "#00CC66"),
        ("failed",    "❌ فشل",          "#FF4444"),
    ]

    task_map: Dict[str, List[Dict]] = {k: [] for k, _, _ in columns_def}
    for t in tasks:
        s = t.get("status", "pending")
        if s == "publishing":
            s = "pending"
        if s in task_map:
            task_map[s].append(t)

    cols = st.columns(len(columns_def))

    for col_widget, (status_key, col_label, col_color) in zip(cols, columns_def):
        col_tasks = task_map[status_key]
        with col_widget:
            # عنوان العمود
            st.markdown(
                f'<div style="background:{col_color}22;border:1px solid {col_color}44;'
                f'border-radius:8px;padding:8px 12px;text-align:center;'
                f'font-weight:bold;color:{col_color};margin-bottom:10px;">'
                f'{col_label} <span style="background:{col_color};color:#000;'
                f'border-radius:10px;padding:0 6px;font-size:12px;">{len(col_tasks)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if not col_tasks:
                st.markdown(
                    '<div style="text-align:center;color:#555;padding:20px 0;">لا توجد مهام</div>',
                    unsafe_allow_html=True,
                )
                continue

            for task in col_tasks:
                _render_kanban_card(task, col_color)


def _render_kanban_card(task: Dict, accent: str):
    from core.database import delete_task
    from core.scheduler import run_task_now

    name    = task.get("name") or "—"
    caption = (task.get("caption") or "").strip()
    caption_preview = (caption[:60] + "…") if len(caption) > 60 else caption
    status  = task.get("status", "pending")

    st.markdown(
        f'<div style="background:#1a1a2e;border:1px solid #333;'
        f'border-top:3px solid {accent};border-radius:8px;'
        f'padding:12px;margin-bottom:8px;direction:rtl;">'

        f'<div style="font-weight:bold;font-size:14px;color:#fff;margin-bottom:6px;">{name}</div>'

        + (f'<div style="color:#aaa;font-size:12px;margin-bottom:6px;">{caption_preview}</div>'
           if caption_preview else "")

        + f'<div style="margin-bottom:6px;">{_plat_badges(task.get("platforms", []))}</div>'

        + (f'<div style="color:#888;font-size:11px;">📅 {_fmt_dt(task.get("scheduled_at"))}</div>'
           if task.get("scheduled_at") else "")

        + (f'<div style="color:#FF6666;font-size:11px;margin-top:4px;">❌ {task["error_msg"][:80]}</div>'
           if task.get("error_msg") else "")

        + f'</div>',
        unsafe_allow_html=True,
    )

    if status in ("pending", "scheduled", "failed"):
        kb1, kb2 = st.columns(2)
        with kb1:
            if st.button("▶️", key=f"kb_now_{task['id']}", help="نشر الآن",
                         use_container_width=True):
                with st.spinner("…"):
                    run_task_now(task["id"])
                st.rerun()
        with kb2:
            if st.button("🗑️", key=f"kb_del_{task['id']}", help="حذف",
                         use_container_width=True):
                delete_task(task["id"])
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# نتيجة النشر — رسالة تفصيلية
# ══════════════════════════════════════════════════════════════════════════════

PLATFORM_LABELS_AR = {
    "tiktok":    "TikTok 🎵",
    "youtube":   "YouTube ▶️",
    "instagram": "Instagram 📸",
    "x":         "X ✖️",
}


def _show_publish_result(task_id: str):
    """عرض نتيجة النشر التفصيلية لكل منصة/حساب بعد المحاولة."""
    from core.database import get_post_history, get_task, get_accounts

    history = get_post_history(task_id=task_id, limit=10)
    if not history:
        st.warning("⚠️ لم تُنفَّذ أي محاولة نشر — تحقق من إعدادات المهمة.")
        return

    task = get_task(task_id) or {}
    status = task.get("status", "")

    successes = [h for h in history if h.get("status") == "success"]
    failures  = [h for h in history if h.get("status") != "success"]

    # نجاحات
    if successes:
        for h in successes:
            plat = h.get("platform", "")
            plat_label = PLATFORM_LABELS_AR.get(plat, plat.upper())
            # ابحث عن اسم الحساب
            accounts = get_accounts(plat)
            acc_name = accounts[0].get("display_name") if accounts else ""
            who = f" — @{acc_name}" if acc_name else ""
            st.success(
                f"✅ تم النشر على **{plat_label}**{who} — "
                f"سيظهر على حسابك خلال دقائق."
            )

    # إخفاقات
    if failures:
        for h in failures:
            plat = h.get("platform", "")
            plat_label = PLATFORM_LABELS_AR.get(plat, plat.upper())
            err = h.get("error_msg") or "خطأ غير معروف"
            st.error(f"❌ فشل النشر على **{plat_label}**: {err[:200]}")

    # حالة إجمالية واضحة
    if status == "failed" and not failures:
        # لم تُحاول النشر إطلاقاً (لا منصات / لا حسابات)
        st.error(f"❌ {task.get('error_msg') or 'لم يتم تنفيذ النشر'}")


# ══════════════════════════════════════════════════════════════════════════════
# سجل النشر
# ══════════════════════════════════════════════════════════════════════════════

def _post_history():
    from core.database import get_post_history

    history = get_post_history(limit=30)
    if not history:
        st.info("لا يوجد سجل نشر بعد.")
        return

    for h in history:
        ok = h["status"] == "success"
        icon = "✅" if ok else "❌"
        color = "#00CC66" if ok else "#FF4444"
        plat = h.get("platform", "").upper()
        st.markdown(
            f'<div style="direction:rtl;padding:6px 0;border-bottom:1px solid #222;'
            f'font-size:13px;">'
            f'<span style="color:{color};font-weight:bold;">{icon}</span> &nbsp;'
            f'<b>{plat}</b> &nbsp;|&nbsp; '
            f'{_fmt_dt(h.get("posted_at"))} &nbsp;'
            + (f'<span style="color:#FF6666;">— {h["error_msg"][:80]}</span>'
               if h.get("error_msg") else "")
            + f'</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# وظائف الجلب والنشر
# ══════════════════════════════════════════════════════════════════════════════

def _pull_from_notion():
    from core.config import get_secret
    from core.notion_client import fetch_ready_tasks
    from core.database import upsert_task

    token = get_secret("notion_token")
    db_id = get_secret("notion_database_id")
    if not token or not db_id:
        st.error("أعدّ توكن Notion وقاعدة البيانات في الإعدادات.")
        return

    with st.spinner("جارٍ جلب المهام من Notion…"):
        try:
            tasks = fetch_ready_tasks(db_id, token)
            for task in tasks:
                upsert_task(task)
            st.success(f"✅ تم جلب {len(tasks)} مهمة.")
        except Exception as e:
            st.error(f"خطأ في الاتصال بـ Notion: {e}")


def _publish_all_pending():
    from core.database import get_all_tasks
    from core.scheduler import run_task_now

    pending = [t for t in get_all_tasks() if t["status"] == "pending"]
    if not pending:
        st.info("لا توجد مهام جاهزة.")
        return

    prog = st.progress(0)
    msg  = st.empty()
    for i, task in enumerate(pending):
        msg.text(f"نشر: {task.get('name', task['id'][:8])}…")
        run_task_now(task["id"])
        prog.progress((i + 1) / len(pending))

    prog.empty()
    msg.empty()
    st.success(f"✅ انتهى نشر {len(pending)} مهمة.")
    st.rerun()
