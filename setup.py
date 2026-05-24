#!/usr/bin/env python3
"""
setup.py — First-time setup wizard for TechVoice Publisher.
Run with: python setup.py
"""
import os
import sys
import subprocess


def colored(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def green(t): return colored(t, "32")
def yellow(t): return colored(t, "33")
def cyan(t): return colored(t, "36")
def red(t): return colored(t, "31")
def bold(t): return colored(t, "1")


def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    """Prompt user for input, with optional masking for secrets."""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    if secret:
        import getpass
        val = getpass.getpass(full_prompt)
    else:
        val = input(full_prompt)

    return val.strip() or default


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    response = input(f"{prompt} [{default_str}]: ").strip().lower()
    if not response:
        return default
    return response in ("y", "yes", "نعم", "ن")


def print_banner():
    print()
    print(cyan("=" * 60))
    print(bold(cyan("   🎬  TechVoice Publisher — إعداد أولي  🎬")))
    print(cyan("=" * 60))
    print()
    print("مرحباً في إعداد تيك فويس للنشر!")
    print("سنقوم بإعداد الأداة خطوة بخطوة.\n")


def ensure_data_dir():
    data_dir = os.path.expanduser("~/.techvoice-publisher")
    tmp_dir = os.path.join(data_dir, "tmp")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)
    print(green(f"✓ مجلد البيانات: {data_dir}"))


def install_requirements():
    print()
    print(bold("📦 تثبيت المتطلبات..."))
    req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")

    if not os.path.exists(req_path):
        print(red("✗ لم يتم العثور على requirements.txt"))
        return False

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_path, "--quiet"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(green("✓ تم تثبيت جميع المتطلبات."))
            return True
        else:
            print(yellow(f"تحذير: {result.stderr[:200]}"))
            return True  # Continue anyway
    except Exception as e:
        print(red(f"خطأ في تثبيت المتطلبات: {e}"))
        return False


def setup_notion():
    print()
    print(bold("🔗 إعداد Notion"))
    print("احصل على Integration Token من: https://www.notion.so/my-integrations")
    print()

    token = ask("أدخل Notion Integration Token", secret=True)
    if not token:
        print(yellow("⚠ تم تخطي إعداد Notion. يمكنك إضافته لاحقاً من الإعدادات."))
        return

    db_id = ask("أدخل Notion Database ID (32 حرفاً من رابط الصفحة)")
    if db_id:
        db_id = db_id.strip().replace("-", "")

    # Store
    from core.config import set_secret
    set_secret("notion_token", token)
    if db_id:
        set_secret("notion_database_id", db_id)

    # Test connection
    if token and db_id:
        print("جارٍ اختبار الاتصال بـ Notion...")
        try:
            from core.notion_client import test_connection
            result = test_connection(db_id, token)
            if result["success"]:
                print(green(f"✓ الاتصال بـ Notion ناجح! قاعدة البيانات: {result['db_title']}"))
            else:
                print(yellow(f"⚠ تحقق من البيانات: {result['message']}"))
        except Exception as e:
            print(yellow(f"⚠ لم يتم التحقق: {e}"))
    else:
        print(green("✓ تم حفظ بيانات Notion."))


def setup_platform(platform: str, label: str, fields: list):
    """Generic platform setup."""
    print()
    print(bold(f"🔑 إعداد {label}"))

    if not ask_yes_no(f"هل تريد إعداد {label} الآن؟"):
        print(yellow(f"⏭ تم تخطي {label}."))
        return

    from core.config import set_secret
    for field_key, field_label, is_secret, placeholder in fields:
        print(f"  {field_label}")
        if placeholder:
            print(f"  ({placeholder})")
        value = ask(f"  أدخل {field_label}", secret=is_secret)
        if value:
            set_secret(field_key, value)
            print(green(f"  ✓ تم حفظ {field_label}"))


def setup_tiktok():
    setup_platform("tiktok", "TikTok", [
        ("tiktok_client_id", "TikTok Client Key", False, "من TikTok Developer Portal"),
        ("tiktok_client_secret", "TikTok Client Secret", True, "من TikTok Developer Portal"),
    ])


def setup_youtube():
    setup_platform("youtube", "YouTube", [
        ("youtube_client_id", "Google OAuth Client ID", False, "من Google Cloud Console → Credentials"),
        ("youtube_client_secret", "Google OAuth Client Secret", True, "من Google Cloud Console"),
    ])


def setup_instagram():
    setup_platform("instagram", "Instagram / Meta", [
        ("instagram_app_id", "Meta App ID", False, "من Meta for Developers → App Dashboard"),
        ("instagram_app_secret", "Meta App Secret", True, "من Meta for Developers"),
    ])


def setup_twitter():
    setup_platform("x", "X (Twitter)", [
        ("twitter_client_id", "X OAuth 2.0 Client ID", False, "من X Developer Portal → App → OAuth 2.0"),
        ("twitter_client_secret", "X OAuth 2.0 Client Secret", True, "من X Developer Portal"),
        ("twitter_bearer_token", "X Bearer Token", True, "من X Developer Portal → App → Keys and tokens"),
    ])


def init_database():
    print()
    print(bold("🗄️ إنشاء قاعدة البيانات..."))
    try:
        from core.database import init_db
        init_db()
        print(green("✓ تم إنشاء قاعدة البيانات بنجاح."))
    except Exception as e:
        print(red(f"✗ خطأ في إنشاء قاعدة البيانات: {e}"))


def print_success():
    print()
    print(cyan("=" * 60))
    print(bold(green("✅ اكتمل الإعداد!")))
    print(cyan("=" * 60))
    print()
    print("لتشغيل التطبيق:")
    print()
    print(bold(cyan("  ./run.sh")))
    print()
    print("أو:")
    print()
    print(bold(cyan("  streamlit run app.py")))
    print()
    print(f"ثم افتح المتصفح على: {cyan('http://localhost:8501')}")
    print()
    print("يمكنك ربط حسابات المنصات من صفحة «ربط الحسابات» داخل التطبيق.")
    print()


def main():
    print_banner()

    # Check Python version
    if sys.version_info < (3, 9):
        print(red("✗ يتطلب Python 3.9 أو أحدث."))
        sys.exit(1)

    # Ensure project root on path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    # Step 1: Install requirements
    if ask_yes_no("هل تريد تثبيت المتطلبات (pip install)؟", default=True):
        install_requirements()

    # Step 2: Create data directories
    ensure_data_dir()

    # Step 3: Notion
    setup_notion()

    # Step 4: Platforms
    print()
    print(bold("📱 إعداد المنصات"))
    print("يمكنك تخطي المنصات الآن وإعدادها لاحقاً من التطبيق.")
    setup_tiktok()
    setup_youtube()
    setup_instagram()
    setup_twitter()

    # Step 5: Init DB
    init_database()

    # Done
    print_success()


if __name__ == "__main__":
    main()
