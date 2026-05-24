"""
settings.py — صفحة الإعدادات الموحّدة.
تحتوي على: Notion + كل منصة (credentials + ربط الحساب) + المُجدوِل.
"""
import streamlit as st


# ── ثوابت المنصات ─────────────────────────────────────────────────────────────

PLATFORMS = {
    "tiktok": {
        "label": "TikTok",
        "icon": "🎵",
        "color": "#ff2d55",
        "desc": "نشر فيديوهات عبر TikTok Content Posting API الرسمي",
        "cred_keys": [
            ("tiktok_client_id",     "Client Key",    False),
            ("tiktok_client_secret", "Client Secret", True),
        ],
        "prereq_keys": ["tiktok_client_id", "tiktok_client_secret"],
        "api_steps": [
            'افتح <a href="https://developers.tiktok.com/" target="_blank" style="color:#7af;">developers.tiktok.com</a> ← اضغط <strong>Developer Portal</strong> (أعلى اليمين) ← افتح تطبيقك',

            '<strong>خطوة 1 — أكمل App details (بيانات التطبيق، الإلزامي بعلامة ★):</strong><br>'
            '• <strong>App icon ★</strong>: أي صورة مربعة 1024×1024 px بصيغة JPG أو PNG<br>'
            '• <strong>App name ★</strong>: <code>TechVoice Publisher</code><br>'
            '• <strong>Category ★</strong>: اختر <strong>Utilities</strong> من القائمة<br>'
            '• <strong>Description ★</strong>: <code>Internal tool for publishing videos to TikTok</code><br>'
            '• <strong>Terms of Service URL ★</strong>: استخدم رابط GitHub Gist أو repo المشروع مثل:<br>'
            '  <code>https://github.com/YOUR_USERNAME/techvoice-publisher</code><br>'
            '  <span style="color:#f90;">⚠️ لا تستخدم example.com — TikTok يرفضه لأنه غير حقيقي</span><br>'
            '• <strong>Privacy Policy URL ★</strong>: نفس الرابط أو رابط GitHub آخر<br>'
            '• <strong>Platforms ★</strong>: ضع ✔ على <strong>Desktop</strong><br>'
            '• <strong>Web/Desktop URL ★</strong> (يظهر تلقائياً عند اختيار Desktop):<br>'
            '  هذا رابط موقع التطبيق الرسمي — استخدم رابط GitHub repo المشروع:<br>'
            '  <code>https://github.com/YOUR_USERNAME/techvoice-publisher</code>',

            '<strong>خطوة 2 — أضف Login Kit أولاً (مطلوب قبل Content Posting API):</strong><br>'
            'اضغط <strong>+ Add products</strong> ← اختر <strong>Login Kit</strong> ← اضغط <strong>+ Add</strong><br>'
            'بعد الإضافة ستظهر إعدادات Login Kit — ابحث عن <strong>Redirect URI</strong> وأضف:<br>'
            '<code>http://localhost:8501/callback/tiktok</code> ← احفظ',

            '<strong>خطوة 3 — أضف Content Posting API:</strong><br>'
            'اضغط <strong>+ Add products</strong> مرة ثانية ←<br>'
            'اختر <strong>Content Posting API</strong> ← اضغط <strong>+ Add</strong><br>'
            '(سيعمل الآن لأن Login Kit مضاف)',

            '<strong>خطوة 4 — أضف Scopes (الصلاحيات المطلوبة):</strong><br>'
            'في قسم <strong>Scopes</strong> اضغط <strong>+ Add scopes</strong> ←<br>'
            'أضف كلاهما:<br>'
            '• <strong>video.publish</strong> — نشر الفيديوهات<br>'
            '• <strong>user.info.basic</strong> — قراءة بيانات الحساب',

            '<strong>خطوة 5 — احفظ وانسخ الـ Credentials:</strong><br>'
            'اضغط <strong>Save</strong> ← ارجع لأعلى الصفحة ← قسم <strong>Credentials</strong>:<br>'
            '• <strong>Client key</strong> (المفتاح): اضغط أيقونة العين ← انسخه في الخانة أدناه<br>'
            '• <strong>Client secret</strong> (السر): اضغط أيقونة العين ← انسخه في الخانة أدناه',

            '<strong style="color:#f90;">⚠️ وضع Draft (مسودة) — طبيعي ومؤقت:</strong><br>'
            '✅ تستطيع الاختبار بحسابك الشخصي مباشرة<br>'
            '⚠️ الفيديوهات ستظهر <strong>خاصة (Private)</strong> في حسابك — هذا متوقع في Draft<br>'
            '📤 للنشر العام مستقبلاً: اضغط <strong>Submit for review</strong> وارفع فيديو demo',
        ],
        "oauth_steps": [
            'تأكد أنك أدخلت <strong>Client Key</strong> و <strong>Client Secret</strong> من Credentials أعلاه',
            'اكتب اسماً للحساب في الخانة أدناه (مثال: <strong>tiktok_main</strong>)',
            'اضغط <strong>"احصل على رابط تسجيل الدخول"</strong>',
            'افتح الرابط في المتصفح ← سجّل دخولك بحساب TikTok',
            'بعد الموافقة سيُعيد توجيهك ← انسخ <strong>الرابط الكامل</strong> من شريط المتصفح',
            'الصق الرابط في خانة <strong>"رابط إعادة التوجيه"</strong> ← اضغط <strong>"اكتمل الربط"</strong>',
            '<strong>ملاحظة Sandbox:</strong> في وضع Draft، سيُنشر الفيديو كـ <strong>خاص (Private)</strong> حتى تحصل على موافقة TikTok',
        ],
    },
    "youtube": {
        "label": "YouTube",
        "icon": "▶️",
        "color": "#FF0000",
        "desc": "رفع فيديوهات YouTube Shorts عبر YouTube Data API v3",
        "cred_keys": [
            ("youtube_client_id",     "Google OAuth Client ID",     False),
            ("youtube_client_secret", "Google OAuth Client Secret", True),
        ],
        "prereq_keys": ["youtube_client_id", "youtube_client_secret"],
        "api_steps": [
            'افتح <a href="https://console.cloud.google.com/" target="_blank" style="color:#7af;">console.cloud.google.com</a>',
            'أنشئ مشروعاً جديداً ← اسمه: <strong>TechVoice</strong>',
            'APIs & Services ← Library ← ابحث عن <strong>YouTube Data API v3</strong> ← Enable',
            'APIs & Services ← Credentials ← <strong>+ Create Credentials ← OAuth Client ID</strong>',
            'Application type: <strong>Desktop app</strong> ← اكتب الاسم ← Create',
            'انسخ <strong>Client ID</strong> و <strong>Client Secret</strong>',
        ],
        "oauth_steps": [
            'أدخل Google Client ID و Client Secret أعلاه أولاً',
            'اكتب اسماً للحساب واضغط "احصل على رابط التسجيل"',
            'افتح الرابط ← سجّل دخولك بـ Google Account صاحب القناة',
            'اسمح بالصلاحيات المطلوبة',
            'انسخ رابط إعادة التوجيه من شريط المتصفح والصقه هنا',
        ],
    },
    "instagram": {
        "label": "Instagram",
        "icon": "📸",
        "color": "#C13584",
        "desc": "نشر Reels وصور Instagram Business/Creator عبر Meta API",
        "cred_keys": [
            ("instagram_app_id",     "Meta App ID",     False),
            ("instagram_app_secret", "Meta App Secret", True),
        ],
        "prereq_keys": ["instagram_app_id", "instagram_app_secret"],
        "api_steps": [
            'افتح <a href="https://developers.facebook.com/" target="_blank" style="color:#7af;">developers.facebook.com</a> وسجّل دخولك',
            'My Apps ← <strong>Create App</strong> ← Other ← Next ← Business ← Next',
            'اكتب اسم التطبيق: <strong>TechVoice Publisher</strong> ← Create App',
            'في لوحة التطبيق: <strong>Add Product ← Instagram ← Set Up</strong>',
            'App Settings ← Basic ← انسخ <strong>App ID</strong> و <strong>App Secret</strong>',
            '<strong>ملاحظة:</strong> حسابك Instagram يجب أن يكون Business أو Creator',
        ],
        "oauth_steps": [
            'أدخل Meta App ID و App Secret أعلاه أولاً',
            'اكتب اسماً للحساب واضغط "احصل على رابط التسجيل"',
            'افتح الرابط ← سجّل دخولك بـ Facebook المرتبط بـ Instagram',
            'انسخ رابط إعادة التوجيه كاملاً والصقه هنا',
        ],
    },
    "x": {
        "label": "X (تويتر)",
        "icon": "✖️",
        "color": "#1DA1F2",
        "desc": "نشر على X — الـ Free Plan يتيح 500 تغريدة شهرياً",
        "cred_keys": [
            ("twitter_client_id",     "X Client ID",     False),
            ("twitter_client_secret", "X Client Secret", True),
            ("twitter_bearer_token",  "Bearer Token",    True),
        ],
        "prereq_keys": ["twitter_client_id"],
        "api_steps": [
            'افتح <a href="https://developer.twitter.com/" target="_blank" style="color:#7af;">developer.twitter.com</a>',
            'Sign up for Free account ← اقبل الشروط',
            'في Dashboard: اضغط <strong>+ Create App</strong>',
            'اكتب اسم التطبيق ← Create',
            'في App Settings ← <strong>User authentication settings</strong>',
            'فعّل <strong>OAuth 2.0</strong> ← اختر <strong>Web App</strong>',
            'Callback URI: <code>http://localhost:8501/callback/x</code>',
            'احفظ ← انسخ <strong>Client ID</strong> و <strong>Client Secret</strong> و <strong>Bearer Token</strong>',
        ],
        "oauth_steps": [
            'أدخل X Client ID و Client Secret أعلاه أولاً',
            'اكتب اسماً للحساب واضغط "احصل على رابط التسجيل"',
            'افتح الرابط ← سجّل دخولك بحسابك على X',
            'اسمح بالصلاحيات',
            'انسخ رابط إعادة التوجيه كاملاً والصقه هنا',
        ],
    },
}


# ── واجهة رئيسية ──────────────────────────────────────────────────────────────

def show():
    from core.config import get_secret, set_secret, is_configured

    st.markdown(
        '<h1 style="text-align:right;direction:rtl;">⚙️ الإعدادات</h1>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🔗 Notion", "🎵 TikTok", "▶️ YouTube", "📸 Instagram", "✖️ X", "⏱️ المُجدوِل"])

    with tabs[0]:
        _notion_tab()

    for idx, platform in enumerate(["tiktok", "youtube", "instagram", "x"], start=1):
        with tabs[idx]:
            _platform_tab(platform, PLATFORMS[platform])

    with tabs[5]:
        _scheduler_tab()


# ══════════════════════════════════════════════════════════════════════════════
# Tab 0 — Notion
# ══════════════════════════════════════════════════════════════════════════════

def _notion_tab():
    from core.config import get_secret, set_secret
    from core.notion_client import test_connection, list_databases

    st.markdown('<h3 style="direction:rtl;">🔗 ربط Notion</h3>', unsafe_allow_html=True)

    # ── تعليمات ──────────────────────────────────────────────────────────────
    with st.expander("📖 كيف أجيب Notion Token؟", expanded=False):
        _steps_box([
            'افتح <a href="https://www.notion.so/my-integrations" target="_blank" style="color:#7af;">notion.so/my-integrations</a>',
            'اضغط <strong>+ New integration</strong>',
            'اكتب الاسم: <strong>TechVoice Publisher</strong> ← اختر Workspace ← Save',
            'انسخ الـ Token — يبدأ بـ <code>ntn_</code> أو <code>secret_</code>',
            '<strong style="color:#f90;">⚠️ مهم:</strong> افتح قاعدة البيانات ← اضغط <strong>···</strong> ← <strong>Connections</strong> ← اختر Integration اللي أنشأته',
        ])

    # ── حالة التوكن ──────────────────────────────────────────────────────────
    _existing_token = get_secret("notion_token") or ""
    _token_ok = bool(_existing_token) and all(ord(c) < 128 for c in _existing_token)

    if _token_ok:
        _status_badge(f"✅ التوكن محفوظ: <code>{_existing_token[:4]}{'•'*8}{_existing_token[-4:]}</code>", "green")
    elif _existing_token:
        st.warning("⚠️ التوكن المحفوظ يحتوي على حروف غير صالحة — أعد إدخاله.")
    else:
        st.info("لا يوجد توكن محفوظ بعد.")

    new_token = st.text_input(
        "Notion Integration Token (اتركه فارغاً إذا لا تريد تغييره)",
        value="", type="password",
        placeholder="ntn_xxxx  أو  secret_xxxx",
        key="notion_token_input",
    )

    if st.button("💾 حفظ التوكن", type="primary", key="save_notion_token"):
        clean = "".join(c for c in new_token if ord(c) < 128).strip()
        if clean and "•" not in clean:
            set_secret("notion_token", clean)
            st.success("✅ تم حفظ التوكن في macOS Keychain")
            st.rerun()
        elif new_token:
            st.error("❌ التوكن يبدو غير صالح — تأكد من نسخه مباشرة من Notion.")
        else:
            st.info("أدخل التوكن أولاً.")

    st.divider()

    # ── قاعدة البيانات ────────────────────────────────────────────────────────
    st.markdown('<h4 style="direction:rtl;">قاعدة البيانات</h4>', unsafe_allow_html=True)

    _saved_db = get_secret("notion_database_id") or ""
    if _saved_db:
        _status_badge(f"✅ قاعدة البيانات محفوظة: <code>{_saved_db[:8]}…</code>", "green")

    col1, col2 = st.columns(2)

    with col1:
        if _token_ok:
            if st.button("📋 اختر قاعدة البيانات من Notion", use_container_width=True, key="fetch_dbs"):
                with st.spinner("جارٍ جلب قواعد البيانات…"):
                    try:
                        dbs = list_databases(get_secret("notion_token"))
                        st.session_state["_notion_dbs"] = dbs
                    except Exception as e:
                        st.error(f"❌ {e}")
                        st.session_state["_notion_dbs"] = []
        else:
            st.button("📋 اختر قاعدة البيانات من Notion", disabled=True,
                      help="احفظ التوكن أولاً", use_container_width=True, key="fetch_dbs_dis")

    with col2:
        if st.button("🔍 اختبر الاتصال", use_container_width=True, key="test_notion"):
            token = get_secret("notion_token")
            db_id = get_secret("notion_database_id")
            if not token or not db_id:
                st.error("يجب حفظ التوكن وقاعدة البيانات أولاً.")
            else:
                with st.spinner("جارٍ الاتصال…"):
                    result = test_connection(db_id, token)
                if result["success"]:
                    st.success(f"✅ ناجح! قاعدة البيانات: **{result['db_title']}**")
                else:
                    st.error(f"❌ {result['message']}")

    # قائمة قواعد البيانات بعد الجلب
    _dbs = st.session_state.get("_notion_dbs")
    if _dbs is not None:
        if not _dbs:
            st.warning("لم يُعثر على قواعد بيانات — تأكد أنك أضفت الـ Integration للقاعدة في Notion.")
        else:
            opts = {f"{d['title']}  ({d['id'][:8]}…)": d["id"] for d in _dbs}
            sel = st.selectbox("اختر قاعدة البيانات:", list(opts.keys()), key="db_picker")
            if st.button("✅ استخدم هذه القاعدة", type="primary", key="use_db"):
                set_secret("notion_database_id", opts[sel])
                st.success(f"✅ تم حفظ: {sel}")
                del st.session_state["_notion_dbs"]
                st.rerun()

    st.divider()

    # ── قيمة "جاهز للنشر" ─────────────────────────────────────────────────────
    st.markdown('<h4 style="direction:rtl;">🏷️ قيمة "جاهز للنشر"</h4>', unsafe_allow_html=True)
    st.markdown(
        '<p style="direction:rtl;color:#aaa;font-size:13px;">'
        'اختر أي قيمة في عمود الحالة تعني "هذا المقطع جاهز للنشر".</p>',
        unsafe_allow_html=True,
    )

    _saved_ready = get_secret("notion_ready_status") or "جاهز للنشر"
    _db_id_now = get_secret("notion_database_id")
    _token_now = get_secret("notion_token")

    if _token_ok and _db_id_now:
        if st.button("🔄 جلب الخيارات من Notion", key="fetch_status_opts"):
            with st.spinner("جارٍ جلب الخيارات…"):
                try:
                    from core.notion_client import get_status_options
                    opts = get_status_options(_db_id_now, _token_now)
                    st.session_state["_status_opts"] = opts
                except Exception as e:
                    st.error(f"❌ {e}")

        _opts_map = st.session_state.get("_status_opts", {})
        if _opts_map:
            all_options = []
            for col, vals in _opts_map.items():
                for v in vals:
                    all_options.append(f"{v}  [{col}]")

            default_idx = 0
            for i, o in enumerate(all_options):
                if _saved_ready in o:
                    default_idx = i
                    break

            selected = st.selectbox(
                "اختر القيمة التي تعني 'جاهز للنشر':",
                all_options,
                index=default_idx,
                key="ready_status_picker",
            )
            # استخرج القيمة بدون اسم العمود
            actual_val = selected.split("  [")[0].strip()

            if st.button("✅ حفظ قيمة الجاهز للنشر", type="primary", key="save_ready_status"):
                set_secret("notion_ready_status", actual_val)
                st.success(f"✅ تم حفظ: **{actual_val}** كقيمة الجاهز للنشر")
                del st.session_state["_status_opts"]
                st.rerun()
        else:
            # عرض القيمة الحالية مع إمكانية تعديلها يدوياً
            new_ready = st.text_input(
                "قيمة الجاهز للنشر",
                value=_saved_ready,
                key="ready_status_manual",
                help="اضغط 'جلب الخيارات' لاختيار من القائمة، أو اكتب القيمة يدوياً",
            )
            if new_ready != _saved_ready:
                if st.button("💾 حفظ", key="save_ready_manual"):
                    set_secret("notion_ready_status", new_ready.strip())
                    st.success(f"✅ تم حفظ: {new_ready}")
                    st.rerun()
            else:
                _status_badge(f"القيمة الحالية: <strong>{_saved_ready}</strong>", "green")
    else:
        st.info("احفظ التوكن وقاعدة البيانات أولاً لتفعيل هذا القسم.", icon="ℹ️")

    st.divider()

    with st.expander("📝 أو أدخل الـ ID يدوياً"):
        raw = st.text_input(
            "رابط قاعدة البيانات أو الـ ID مباشرة",
            value=_saved_db,
            placeholder="https://www.notion.so/…  أو  الـ ID مباشرة",
            key="notion_db_manual",
        )
        db_id_extracted = _extract_notion_db_id(raw)
        if raw and db_id_extracted and db_id_extracted != raw.strip():
            st.caption(f"✨ ID المستخرج: `{db_id_extracted}`")
        if st.button("💾 حفظ الـ ID", key="save_db_manual"):
            if db_id_extracted:
                set_secret("notion_database_id", db_id_extracted.replace("-", ""))
                st.success("✅ تم حفظ الـ ID")
                st.rerun()
            else:
                st.info("أدخل الرابط أو الـ ID أولاً.")


# ══════════════════════════════════════════════════════════════════════════════
# Tab 1-4 — Platform
# ══════════════════════════════════════════════════════════════════════════════

def _platform_tab(platform: str, info: dict):
    from core.config import get_secret, set_secret
    from core.database import get_accounts, delete_account

    st.markdown(
        f'<h3 style="direction:rtl;color:{info["color"]};">'
        f'{info["icon"]} {info["label"]}</h3>'
        f'<p style="direction:rtl;color:#aaa;">{info["desc"]}</p>',
        unsafe_allow_html=True,
    )

    # ── الحسابات المرتبطة ────────────────────────────────────────────────────
    accounts = get_accounts(platform)
    if accounts:
        st.markdown('<div style="direction:rtl;margin-bottom:8px;"><strong>الحسابات المرتبطة:</strong></div>',
                    unsafe_allow_html=True)
        for acc in accounts:
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                st.markdown(f'<span style="direction:rtl;">👤 {acc.get("display_name","—")}</span>',
                            unsafe_allow_html=True)
            with c2:
                st.markdown('<span style="color:#00CC66;font-size:12px;">● متصل</span>',
                            unsafe_allow_html=True)
            with c3:
                if st.button("🗑️", key=f"del_{platform}_{acc['id']}"):
                    delete_account(acc["id"])
                    from core.config import delete_secret
                    for suffix in ["access_token", "refresh_token", "tokens"]:
                        delete_secret(f"{platform}_{suffix}_{acc['id']}")
                    st.rerun()
    else:
        st.info(f"لا توجد حسابات {info['label']} مرتبطة.", icon="ℹ️")

    st.divider()

    # ── بيانات الـ API ────────────────────────────────────────────────────────
    with st.expander(f"🔑 بيانات API — {info['label']}", expanded=not _platform_is_configured(platform)):
        with st.container():
            st.markdown('<div style="direction:rtl;margin-bottom:6px;color:#aaa;font-size:13px;">'
                        '📖 خطوات الحصول على بيانات API:</div>', unsafe_allow_html=True)
            _steps_box(info["api_steps"])

        for key, label, is_secret in info["cred_keys"]:
            _credential_row(key, label, is_secret, platform)

    # ── ربط حساب جديد ────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div style="direction:rtl;font-weight:600;margin-bottom:8px;">➕ ربط حساب جديد</div>',
                unsafe_allow_html=True)

    if not _platform_is_configured(platform):
        st.warning(f"أدخل بيانات API لـ {info['label']} أولاً من القسم أعلاه.", icon="⚠️")
        return

    with st.expander("📖 خطوات الربط", expanded=False):
        _steps_box(info["oauth_steps"])

    _oauth_connect_ui(platform, info)


# ══════════════════════════════════════════════════════════════════════════════
# Tab 5 — Scheduler
# ══════════════════════════════════════════════════════════════════════════════

def _scheduler_tab():
    from core.scheduler import is_running, start_scheduler, stop_scheduler

    st.markdown('<h3 style="direction:rtl;">⏱️ المُجدوِل التلقائي</h3>', unsafe_allow_html=True)
    st.markdown(
        '<p style="direction:rtl;color:#aaa;">يفحص المهام المجدولة كل 5 دقائق وينشرها تلقائياً عند موعدها.</p>',
        unsafe_allow_html=True,
    )

    running = is_running()
    if running:
        _status_badge("✅ المُجدوِل يعمل — يفحص كل 5 دقائق", "green")
        if st.button("⏸ إيقاف المُجدوِل", key="stop_sched"):
            stop_scheduler()
            st.rerun()
    else:
        _status_badge("⏸ المُجدوِل متوقف", "red")
        if st.button("▶️ تشغيل المُجدوِل", type="primary", key="start_sched"):
            start_scheduler()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# دوال OAuth
# ══════════════════════════════════════════════════════════════════════════════

def _oauth_connect_ui(platform: str, info: dict):
    """واجهة OAuth موحّدة لكل المنصات."""
    publisher = _get_publisher_instance(platform)
    if publisher is None:
        st.error(f"تعذّر تحميل ناشر {info['label']} — راجع الإعدادات أعلاه.")
        return

    account_name = st.text_input(
        "اسم الحساب",
        placeholder=f"مثال: {platform}_main",
        key=f"acc_name_{platform}",
    )

    if st.button(f"🔑 احصل على رابط تسجيل الدخول", key=f"get_url_{platform}", type="primary"):
        if not account_name.strip():
            st.warning("أدخل اسماً للحساب أولاً.")
        else:
            try:
                url = publisher.get_auth_url()
                if url:
                    st.session_state[f"auth_url_{platform}"] = url
                    st.session_state[f"auth_name_{platform}"] = account_name.strip()
                else:
                    st.error("تعذّر إنشاء رابط التسجيل.")
            except Exception as e:
                st.error(f"خطأ: {e}")

    if f"auth_url_{platform}" in st.session_state:
        auth_url = st.session_state[f"auth_url_{platform}"]
        st.markdown(
            '<div style="direction:rtl;margin:10px 0 4px;color:#aaa;font-size:13px;">'
            'افتح هذا الرابط في المتصفح، سجّل الدخول، ثم انسخ رابط إعادة التوجيه:</div>',
            unsafe_allow_html=True,
        )
        st.link_button("🌐 افتح رابط تسجيل الدخول", auth_url, use_container_width=True)

        callback_url = st.text_input(
            "الصق رابط إعادة التوجيه هنا",
            placeholder="http://localhost:8501/callback/...",
            key=f"cb_{platform}",
        )

        if st.button("✅ اكتمل الربط", key=f"done_{platform}"):
            code, state = _extract_code_state(callback_url)
            if not code:
                st.error("لم يُعثر على الكود في الرابط. انسخ الرابط كاملاً من شريط المتصفح.")
            else:
                saved_name = st.session_state.get(f"auth_name_{platform}", account_name)
                with st.spinner(f"جارٍ ربط حساب {info['label']}…"):
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
                    st.error("فشل الربط — تأكد من صحة الرابط أو أعد المحاولة.")


def _extract_code_state(callback_url: str):
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(callback_url)
        qs = urllib.parse.parse_qs(parsed.query)
        return qs.get("code", [None])[0], qs.get("state", [""])[0]
    except Exception:
        return None, ""


def _platform_is_configured(platform: str) -> bool:
    from core.config import get_secret
    checks = {
        "tiktok":    lambda: get_secret("tiktok_client_id") and get_secret("tiktok_client_secret"),
        "youtube":   lambda: get_secret("youtube_client_id") and get_secret("youtube_client_secret"),
        "instagram": lambda: get_secret("instagram_app_id") and get_secret("instagram_app_secret"),
        "x":         lambda: get_secret("twitter_client_id"),
    }
    fn = checks.get(platform)
    return bool(fn and fn())


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


# ══════════════════════════════════════════════════════════════════════════════
# دوال مساعدة للـ Credentials
# ══════════════════════════════════════════════════════════════════════════════

def _credential_row(key: str, label: str, is_secret: bool, platform: str):
    """صف credential واحد مع زر حفظ."""
    from core.config import get_secret, set_secret

    current = get_secret(key) or ""
    display = (current[:4] + "•" * 8 + current[-4:]) if (is_secret and len(current) > 8) else current

    col1, col2 = st.columns([5, 1])
    with col1:
        new_val = st.text_input(
            label,
            value="" if is_secret else current,
            placeholder=display if (is_secret and current) else f"أدخل {label}",
            type="password" if is_secret else "default",
            key=f"cred_{platform}_{key}",
        )
    with col2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("💾", key=f"save_{platform}_{key}", help=f"حفظ {label}", use_container_width=True):
            clean = "".join(c for c in new_val if ord(c) < 128).strip()
            if clean and "•" not in clean:
                set_secret(key, clean)
                st.success(f"✅ {label} محفوظ")
            elif new_val:
                st.error("❌ القيمة غير صالحة")
            else:
                st.info("لا تغيير")

    if current and is_secret:
        st.caption(f"{'✅ محفوظ'}: `{display}`")


# ══════════════════════════════════════════════════════════════════════════════
# دوال مساعدة للعرض
# ══════════════════════════════════════════════════════════════════════════════

def _steps_box(steps: list):
    html = "".join(
        f'<div style="margin:6px 0;direction:rtl;">'
        f'<span style="background:#2d2d44;color:#aef;border-radius:50%;'
        f'width:22px;height:22px;display:inline-flex;align-items:center;'
        f'justify-content:center;font-size:12px;margin-left:8px;">{i+1}</span>'
        f'{step}</div>'
        for i, step in enumerate(steps)
    )
    st.markdown(
        f'<div style="background:#16162a;border:1px solid #333;border-radius:8px;'
        f'padding:14px 16px;margin:8px 0 12px 0;">{html}</div>',
        unsafe_allow_html=True,
    )


def _status_badge(html_text: str, color: str = "green"):
    bg = "#1a2a1a" if color == "green" else "#2a1a1a"
    border = "#2a5" if color == "green" else "#a33"
    st.markdown(
        f'<div style="direction:rtl;padding:7px 12px;background:{bg};border:1px solid {border};'
        f'border-radius:6px;margin:6px 0 10px 0;">{html_text}</div>',
        unsafe_allow_html=True,
    )


def _extract_notion_db_id(raw: str) -> str:
    import re
    if not raw:
        return ""
    raw = raw.strip()
    m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', raw, re.IGNORECASE)
    if m:
        return m.group(1).replace("-", "")
    m = re.search(r'([0-9a-f]{32})', raw, re.IGNORECASE)
    if m:
        return m.group(1)
    cleaned = raw.replace("-", "").lower()
    import re as _re
    if _re.fullmatch(r'[0-9a-f]{32}', cleaned):
        return cleaned
    return raw
