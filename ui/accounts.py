"""
accounts.py — Page 2: Connect/disconnect social media accounts.
"""
import streamlit as st
from typing import Optional


PLATFORM_INFO = {
    "tiktok": {
        "label": "TikTok",
        "icon": "🎵",
        "color": "#ff2d55",
        "desc": "نشر فيديوهات على TikTok عبر Content Posting API الرسمي",
        "prereq_keys": ["tiktok_client_id", "tiktok_client_secret"],
        "prereq_hint": "يجب إدخال TikTok Client Key و Client Secret في الإعدادات أولاً.",
        "oauth_steps": [
            "تأكد أنك أدخلت Client Key و Client Secret في ⚙️ الإعدادات",
            'اكتب اسماً للحساب (مثل: <strong>tiktok_main</strong>)',
            'اضغط "احصل على رابط تسجيل الدخول"',
            "افتح الرابط في المتصفح وسجّل دخولك بحساب TikTok",
            "بعد تسجيل الدخول، سيعيد توجيهك — انسخ الرابط الكامل من شريط المتصفح",
            'الصقه في خانة "رابط إعادة التوجيه" ← اضغط "اكتمل الربط"',
        ],
    },
    "youtube": {
        "label": "YouTube",
        "icon": "▶️",
        "color": "#FF0000",
        "desc": "رفع فيديوهات YouTube Shorts عبر YouTube Data API v3",
        "prereq_keys": ["youtube_client_id", "youtube_client_secret"],
        "prereq_hint": "يجب إدخال Google OAuth Client ID و Client Secret في الإعدادات أولاً.",
        "oauth_steps": [
            "تأكد أنك أدخلت Google Client ID و Client Secret في ⚙️ الإعدادات",
            'اكتب اسماً للحساب (مثل: <strong>youtube_main</strong>)',
            'اضغط "احصل على رابط تسجيل الدخول"',
            "افتح الرابط ← سجّل دخولك بـ Google Account صاحب القناة",
            "اسمح بالصلاحيات المطلوبة",
            "انسخ الرابط الكامل من المتصفح بعد التحويل والصقه هنا",
        ],
    },
    "instagram": {
        "label": "Instagram",
        "icon": "📸",
        "color": "#C13584",
        "desc": "نشر Reels وصور على Instagram Business/Creator عبر Meta API",
        "prereq_keys": ["instagram_app_id", "instagram_app_secret"],
        "prereq_hint": "يجب إدخال Meta App ID و App Secret في الإعدادات أولاً. تأكد أن حسابك Instagram Business أو Creator.",
        "oauth_steps": [
            "تأكد أنك أدخلت Meta App ID و App Secret في ⚙️ الإعدادات",
            "تأكد أن حسابك Instagram نوعه <strong>Business</strong> أو <strong>Creator</strong>",
            'اكتب اسماً للحساب (مثل: <strong>instagram_main</strong>)',
            'اضغط "احصل على رابط تسجيل الدخول"',
            "افتح الرابط ← سجّل دخولك بـ Facebook المرتبط بـ Instagram",
            "انسخ رابط إعادة التوجيه كاملاً والصقه هنا",
        ],
    },
    "x": {
        "label": "X (تويتر)",
        "icon": "✖️",
        "color": "#1DA1F2",
        "desc": "نشر تغريدات ومقاطع على X — الـ Free Plan يتيح 500 تغريدة/شهر",
        "prereq_keys": ["twitter_client_id"],
        "prereq_hint": "يجب إدخال X Client ID في الإعدادات أولاً.",
        "oauth_steps": [
            "تأكد أنك أدخلت X Client ID و Client Secret في ⚙️ الإعدادات",
            'اكتب اسماً للحساب (مثل: <strong>x_main</strong>)',
            'اضغط "احصل على رابط تسجيل الدخول"',
            "افتح الرابط ← سجّل دخولك بحسابك على X",
            "اسمح بالصلاحيات",
            "انسخ رابط إعادة التوجيه كاملاً والصقه هنا",
        ],
    },
}


def _steps_box(steps: list):
    """عرض مربع خطوات موحّد."""
    steps_html = "".join(
        f'<div style="margin:6px 0;direction:rtl;">'
        f'<span style="background:#2d2d44;color:#aef;border-radius:50%;'
        f'width:22px;height:22px;display:inline-flex;align-items:center;'
        f'justify-content:center;font-size:12px;margin-left:8px;">{i+1}</span>'
        f'{step}</div>'
        for i, step in enumerate(steps)
    )
    st.markdown(
        f'<div style="background:#16162a;border:1px solid #333;border-radius:8px;'
        f'padding:14px 16px;margin:8px 0 12px 0;">{steps_html}</div>',
        unsafe_allow_html=True,
    )


def show():
    from core.database import get_accounts, delete_account
    from core.config import get_secret

    st.markdown(
        '<h1 style="text-align:right;direction:rtl;">🔗 ربط الحسابات</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:right;direction:rtl;color:#aaa;">'
        'اربط حسابات المنصات لتتمكن من النشر التلقائي. '
        'لكل منصة خطوات موضّحة بالتفصيل.</p>',
        unsafe_allow_html=True,
    )

    for platform, info in PLATFORM_INFO.items():
        if platform == "tiktok":
            _render_tiktok_section(info)
        else:
            _render_platform_section(platform, info)


def _render_platform_section(platform: str, info: dict):
    from core.database import get_accounts, delete_account
    from core.config import get_secret

    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(
            f'<div style="font-size:48px;text-align:center;">{info["icon"]}</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<h3 style="direction:rtl;color:{info["color"]};">{info["label"]}</h3>'
            f'<p style="direction:rtl;color:#aaa;">{info["desc"]}</p>',
            unsafe_allow_html=True,
        )

    # ── خطوات الربط ──────────────────────────────────────────────────────
    with st.expander(f"📖 كيف أربط حساب {info['label']}؟", expanded=False):
        _steps_box(info.get("oauth_steps", []))
        prereq = info.get("prereq_hint", "")
        if prereq:
            st.info(f"**قبل البدء:** {prereq}", icon="⚠️")

    accounts = get_accounts(platform)

    if accounts:
        st.markdown('<div style="direction:rtl;">', unsafe_allow_html=True)
        for acc in accounts:
            col_a, col_b, col_c = st.columns([3, 2, 1])
            with col_a:
                st.markdown(
                    f'<span style="direction:rtl;">👤 {acc.get("display_name","—")}</span>',
                    unsafe_allow_html=True,
                )
            with col_b:
                st.markdown(
                    f'<span style="color:#00CC66;font-size:12px;">● متصل</span>',
                    unsafe_allow_html=True,
                )
            with col_c:
                if st.button("🗑️ حذف", key=f"del_acc_{acc['id']}"):
                    delete_account(acc["id"])
                    from core.config import delete_secret
                    delete_secret(f"{platform}_access_token_{acc['id']}")
                    delete_secret(f"{platform}_refresh_token_{acc['id']}")
                    delete_secret(f"{platform}_tokens_{acc['id']}")
                    st.success(f"تم حذف حساب {acc.get('display_name','')}")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info(f"لا توجد حسابات {info['label']} مرتبطة.", icon="ℹ️")

    # Connect new account section
    with st.expander(f"➕ ربط حساب {info['label']} جديد"):
        _connect_account_ui(platform, info)


def _connect_account_ui(platform: str, info: dict):
    from core.config import get_secret

    st.markdown(
        '<div style="direction:rtl;">',
        unsafe_allow_html=True,
    )

    # Check prerequisites
    if not _platform_is_configured(platform):
        st.warning(
            f"يرجى إدخال بيانات API لـ {info['label']} في الإعدادات أولاً "
            f"(Client ID و Client Secret).",
            icon="⚠️",
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    publisher = _get_publisher_instance(platform)
    if publisher is None:
        st.error(f"لم يتم تحميل ناشر {info['label']}. تأكد من الإعدادات.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    account_name = st.text_input(
        "اسم الحساب (للتعريف فقط)",
        placeholder=f"مثال: {info['label']}_main",
        key=f"acc_name_{platform}",
    )

    if st.button(f"🔑 احصل على رابط تسجيل الدخول لـ {info['label']}", key=f"auth_url_{platform}"):
        if not account_name:
            st.warning("يرجى إدخال اسم للحساب أولاً.")
        else:
            try:
                url = publisher.get_auth_url()
                if url:
                    st.session_state[f"auth_url_{platform}"] = url
                    st.session_state[f"acc_name_saved_{platform}"] = account_name
                else:
                    st.error("تعذّر إنشاء رابط التسجيل. تحقق من الإعدادات.")
            except Exception as e:
                st.error(f"خطأ: {e}")

    if f"auth_url_{platform}" in st.session_state:
        auth_url = st.session_state[f"auth_url_{platform}"]
        st.markdown(
            f'<div style="direction:rtl;margin:12px 0;">'
            f'<strong>افتح هذا الرابط في المتصفح، سجّل الدخول، ثم انسخ رابط إعادة التوجيه:</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.code(auth_url, language=None)
        st.link_button("🌐 افتح رابط التسجيل", auth_url)

        callback_url = st.text_input(
            "الصق رابط إعادة التوجيه هنا (بعد تسجيل الدخول)",
            placeholder="http://localhost:8501/callback/...",
            key=f"callback_{platform}",
        )

        if st.button("✅ اكتمل الربط", key=f"complete_{platform}"):
            if not callback_url:
                st.warning("يرجى لصق رابط إعادة التوجيه.")
            else:
                code, state = _extract_code_state(callback_url)
                if not code:
                    st.error("لم يتم العثور على الكود في الرابط. تأكد من نسخ الرابط كاملاً.")
                else:
                    saved_name = st.session_state.get(f"acc_name_saved_{platform}", account_name)
                    with st.spinner(f"جارٍ ربط حساب {info['label']}..."):
                        try:
                            if platform == "x" and state:
                                success = publisher.handle_callback(code, saved_name, state=state)
                            else:
                                success = publisher.handle_callback(code, saved_name)
                        except Exception as e:
                            st.error(f"خطأ أثناء الربط: {e}")
                            success = False

                    if success:
                        st.success(f"✅ تم ربط حساب {info['label']} بنجاح!")
                        del st.session_state[f"auth_url_{platform}"]
                        st.rerun()
                    else:
                        st.error("فشل الربط. تأكد من صحة الرابط وأن التوكن لم ينتهِ.")

    st.markdown("</div>", unsafe_allow_html=True)


def _extract_code_state(callback_url: str):
    """Extract code and state from callback URL."""
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(callback_url)
        qs = urllib.parse.parse_qs(parsed.query)
        code = qs.get("code", [None])[0]
        state = qs.get("state", [""])[0]
        return code, state
    except Exception:
        return None, ""


def _platform_is_configured(platform: str) -> bool:
    from core.config import get_secret
    checks = {
        "tiktok": lambda: get_secret("tiktok_client_id") and get_secret("tiktok_client_secret"),
        "youtube": lambda: get_secret("youtube_client_id") and get_secret("youtube_client_secret"),
        "instagram": lambda: (get_secret("instagram_app_id") or get_secret("tiktok_client_id")),
        "x": lambda: get_secret("twitter_client_id"),
    }
    check = checks.get(platform)
    return bool(check and check())


def _get_publisher_instance(platform: str):
    from core.config import get_secret
    try:
        if platform == "tiktok":
            from platforms.tiktok import TikTokPublisher
            return TikTokPublisher(get_secret("tiktok_client_id"), get_secret("tiktok_client_secret"))
        elif platform == "youtube":
            from platforms.youtube import YouTubePublisher
            return YouTubePublisher(get_secret("youtube_client_id"), get_secret("youtube_client_secret"))
        elif platform == "instagram":
            from platforms.instagram import InstagramPublisher
            return InstagramPublisher()
        elif platform == "x":
            from platforms.twitter import TwitterPublisher
            return TwitterPublisher(
                get_secret("twitter_bearer_token") or "",
                get_secret("twitter_client_id") or "",
                get_secret("twitter_client_secret") or "",
            )
    except Exception as e:
        st.error(f"خطأ في تحميل ناشر {platform}: {e}")
    return None


# ══════════════════════════════════════════════════════════════════
# TikTok — طريقتان للربط
# ══════════════════════════════════════════════════════════════════

def _render_tiktok_section(info: dict):
    """TikTok — الطريقة الرسمية فقط عبر Content Posting API."""
    from core.database import get_accounts, delete_account

    st.divider()
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown('<div style="font-size:48px;text-align:center;">🎵</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(
            f'<h3 style="direction:rtl;color:{info["color"]};">TikTok</h3>'
            f'<p style="direction:rtl;color:#aaa;">{info["desc"]}</p>',
            unsafe_allow_html=True,
        )

    # ── الحسابات المرتبطة ────────────────────────────────────────────────
    accounts = get_accounts("tiktok")
    if accounts:
        for acc in accounts:
            col_a, col_b, col_c = st.columns([3, 2, 1])
            with col_a:
                st.markdown(
                    f'<span style="direction:rtl;">👤 {acc.get("display_name","—")}</span>',
                    unsafe_allow_html=True,
                )
            with col_b:
                st.markdown('<span style="color:#00CC66;font-size:12px;">● متصل</span>', unsafe_allow_html=True)
            with col_c:
                if st.button("🗑️", key=f"del_tiktok_{acc['id']}"):
                    delete_account(acc["id"])
                    st.rerun()
    else:
        st.info("لا توجد حسابات TikTok مرتبطة.", icon="ℹ️")

    _tiktok_api_connect()


def _tiktok_api_connect():
    """الطريقة الرسمية — TikTok Content Posting API."""
    from core.config import get_secret

    with st.expander("📖 كيف أجيب بيانات API الرسمي؟", expanded=False):
        _steps_box([
            'افتح <strong>developers.tiktok.com</strong> ← Manage Apps',
            'أنشئ تطبيقاً جديداً وأضف <strong>Content Posting API</strong>',
            'في Redirect URI اكتب: <code>http://localhost:8501/callback/tiktok</code>',
            'انسخ <strong>Client Key</strong> و <strong>Client Secret</strong> وأدخلهما في الإعدادات ⚙️',
            'ارجع هنا واضغط "احصل على رابط التسجيل"',
            'سجّل دخولك بحساب TikTok ← انسخ رابط إعادة التوجيه ← الصقه هنا',
        ])
        st.info("بعد الموافقة من TikTok (Audit)، تنشر المقاطع بشكل عام. بدونها تُحفظ خاصة فقط.", icon="ℹ️")

    if not (get_secret("tiktok_client_id") and get_secret("tiktok_client_secret")):
        st.warning("⚠️ أدخل Client Key و Client Secret في ⚙️ الإعدادات أولاً.", icon="⚠️")
        return

    account_name = st.text_input("اسم الحساب", placeholder="tiktok_main", key="tiktok_api_name")

    if st.button("🔑 احصل على رابط تسجيل الدخول", key="tiktok_api_auth"):
        if not account_name:
            st.warning("أدخل اسماً للحساب.")
        else:
            try:
                from platforms.tiktok import TikTokPublisher
                pub = TikTokPublisher(get_secret("tiktok_client_id"), get_secret("tiktok_client_secret"))
                url = pub.get_auth_url()
                st.session_state["tiktok_api_auth_url"] = url
                st.session_state["tiktok_api_acc_name"] = account_name
            except Exception as e:
                st.error(f"خطأ: {e}")

    if "tiktok_api_auth_url" in st.session_state:
        st.code(st.session_state["tiktok_api_auth_url"], language=None)
        st.link_button("🌐 افتح رابط التسجيل", st.session_state["tiktok_api_auth_url"])
        callback = st.text_input(
            "الصق رابط إعادة التوجيه بعد تسجيل الدخول",
            placeholder="http://localhost:8501/callback/tiktok?code=...",
            key="tiktok_api_callback",
        )
        if st.button("✅ اكتمل الربط", key="tiktok_api_complete"):
            code, _ = _extract_code_state(callback)
            if not code:
                st.error("ما وُجد كود في الرابط. انسخ الرابط كاملاً.")
            else:
                from platforms.tiktok import TikTokPublisher
                pub = TikTokPublisher(get_secret("tiktok_client_id"), get_secret("tiktok_client_secret"))
                with st.spinner("جارٍ الربط..."):
                    ok = pub.handle_callback(code, st.session_state.get("tiktok_api_acc_name", "main"))
                if ok:
                    st.success("✅ تم ربط حساب TikTok بالطريقة الرسمية!")
                    del st.session_state["tiktok_api_auth_url"]
                    st.rerun()
                else:
                    st.error("فشل الربط. تأكد من صحة الرابط.")


