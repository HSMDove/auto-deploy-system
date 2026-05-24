"""
notion_client.py — Fetch tasks and update statuses via the Notion API.
Supports both Arabic and English property names.
Compatible with notion-client 3.x (databases.query removed — uses direct request).
"""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Arabic ↔ English property name mappings
PROP_NAME = ["الاسم", "Name"]
PROP_STATUS = ["الحالة", "Status"]
PROP_VIDEO_URL = ["رابط الفيديو", "Video URL"]
PROP_COVER_URL = ["رابط الكفر", "Cover URL"]
PROP_CAPTION = ["الكابشن", "Caption"]
PROP_PLATFORMS = ["المنصات", "Platforms"]
PROP_SCHEDULED_AT = ["وقت النشر", "Scheduled At"]
PROP_CONTENT_TYPE = ["نوع المحتوى", "Content Type"]

STATUS_READY = "جاهز للنشر"
STATUS_PUBLISHING = "جارٍ النشر"
STATUS_DONE = "تم النشر"
STATUS_FAILED = "فشل النشر"

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"


def _clean_token(token: str) -> str:
    """Strip non-ASCII / invisible unicode chars (RTL marks, mask bullets •, etc.)."""
    cleaned = "".join(c for c in token if ord(c) < 128).strip()
    if not cleaned:
        raise ValueError("Notion token is empty or contains only non-ASCII characters.")
    return cleaned


def _get_client(token: str):
    """Import and return a Notion Client instance (for endpoints that still exist)."""
    from notion_client import Client  # type: ignore
    return Client(auth=_clean_token(token))


def _notion_headers(token: str) -> Dict[str, str]:
    """Return standard Notion API headers."""
    return {
        "Authorization": f"Bearer {_clean_token(token)}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _find_prop(properties: Dict[str, Any], candidates: List[str]) -> Optional[Any]:
    """Return the first matching property value from a list of candidate names."""
    for name in candidates:
        if name in properties:
            return properties[name]
    return None


def _extract_text(prop: Optional[Dict]) -> str:
    """Extract plain text from a Notion title or rich_text property."""
    if not prop:
        return ""
    prop_type = prop.get("type")
    items = prop.get(prop_type, [])
    if isinstance(items, list):
        return "".join(item.get("plain_text", "") for item in items)
    return ""


def _extract_url(prop: Optional[Dict]) -> Optional[str]:
    """Extract URL string from a Notion url property."""
    if not prop:
        return None
    return prop.get("url")


def _extract_multi_select(prop: Optional[Dict]) -> List[str]:
    """Extract names from a Notion multi_select property."""
    if not prop:
        return []
    return [opt.get("name", "") for opt in prop.get("multi_select", [])]


def _extract_date(prop: Optional[Dict]) -> Optional[str]:
    """Extract start date string from a Notion date property."""
    if not prop:
        return None
    date_obj = prop.get("date")
    if date_obj:
        return date_obj.get("start")
    return None


def _extract_select(prop: Optional[Dict]) -> Optional[str]:
    """Extract name from a Notion select property."""
    if not prop:
        return None
    select_obj = prop.get("select")
    if select_obj:
        return select_obj.get("name")
    return None


def _page_to_task(page: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw Notion page dict to our task dict."""
    props = page.get("properties", {})

    # ── الاسم: ابحث عن خاصية type=title أولاً (مهما كان اسمها)
    name = ""
    for prop_info in props.values():
        if prop_info.get("type") == "title":
            name = _extract_text(prop_info)
            break
    if not name:
        name = _extract_text(_find_prop(props, PROP_NAME))
    video_url = _extract_url(_find_prop(props, PROP_VIDEO_URL))
    cover_url = _extract_url(_find_prop(props, PROP_COVER_URL))
    caption_raw = _find_prop(props, PROP_CAPTION)
    caption = _extract_text(caption_raw) if caption_raw else ""
    platforms = _extract_multi_select(_find_prop(props, PROP_PLATFORMS))
    scheduled_at = _extract_date(_find_prop(props, PROP_SCHEDULED_AT))
    content_type = _extract_select(_find_prop(props, PROP_CONTENT_TYPE)) or "video"

    # Normalize platform names to lowercase ascii keys
    platform_map = {
        "tiktok": "tiktok", "تيك توك": "tiktok", "tikTok": "tiktok",
        "youtube": "youtube", "يوتيوب": "youtube", "YouTube": "youtube",
        "instagram": "instagram", "إنستغرام": "instagram", "انستقرام": "instagram",
        "x": "x", "twitter": "x", "تويتر": "x", "X": "x",
    }
    normalized_platforms = []
    for p in platforms:
        key = platform_map.get(p, p.lower())
        if key not in normalized_platforms:
            normalized_platforms.append(key)

    return {
        "id": page["id"],
        "name": name,
        "status": "pending",
        "video_url": video_url,
        "cover_url": cover_url,
        "caption": caption,
        "platforms": normalized_platforms,
        "scheduled_at": scheduled_at,
        "content_type": content_type.lower() if content_type else "video",
        "created_at": page.get("created_time"),
    }


def get_status_options(database_id: str, token: str) -> Dict[str, List[str]]:
    """
    Return a dict of {prop_name: [option1, option2, ...]} for every
    select/status/multi_select property in the database.
    Used by the settings UI to let the user pick the "ready" value.
    """
    import httpx
    headers = _notion_headers(token)
    try:
        resp = httpx.get(
            f"{NOTION_BASE_URL}/databases/{database_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        props = resp.json().get("properties", {})
    except Exception as e:
        logger.error("Could not fetch schema: %s", e)
        return {}

    result: Dict[str, List[str]] = {}
    for prop_name, prop_info in props.items():
        ptype = prop_info.get("type", "")
        if ptype == "status":
            opts = [
                o.get("name", "")
                for g in prop_info.get("status", {}).get("groups", [])
                for o in g.get("options", [])
            ]
            # fallback: flat options list
            if not opts:
                opts = [o.get("name", "") for o in prop_info.get("status", {}).get("options", [])]
        elif ptype == "select":
            opts = [o.get("name", "") for o in prop_info.get("select", {}).get("options", [])]
        elif ptype == "multi_select":
            opts = [o.get("name", "") for o in prop_info.get("multi_select", {}).get("options", [])]
        else:
            continue
        result[prop_name] = [o for o in opts if o]
    return result


def _find_working_filter(
    database_id: str,
    headers: Dict[str, str],
    ready_value: str,
) -> Optional[Dict[str, Any]]:
    """
    Find the first (property_name, property_type) combination that Notion
    accepts for filtering by the given ready_value.
    Uses the actual schema to match real options.
    """
    import httpx

    candidate_pairs: List[tuple] = []
    try:
        schema_resp = httpx.get(
            f"{NOTION_BASE_URL}/databases/{database_id}",
            headers=headers,
            timeout=15,
        )
        if schema_resp.status_code == 200:
            props = schema_resp.json().get("properties", {})
            for prop_name, prop_info in props.items():
                ptype = prop_info.get("type", "")
                if ptype in ("status", "select", "multi_select"):
                    candidate_pairs.append((prop_name, ptype))
    except Exception as e:
        logger.warning("Could not fetch DB schema: %s", e)

    # Fallback hard-coded names
    for name in ["الحالة", "Status", "الحاله", "state"]:
        for ptype in ["status", "select"]:
            if (name, ptype) not in candidate_pairs:
                candidate_pairs.append((name, ptype))

    for prop_name, prop_type in candidate_pairs:
        if prop_type == "multi_select":
            filter_clause = {"property": prop_name, "multi_select": {"contains": ready_value}}
        else:
            filter_clause = {"property": prop_name, prop_type: {"equals": ready_value}}

        body = {"filter": filter_clause, "page_size": 1}
        try:
            resp = httpx.post(
                f"{NOTION_BASE_URL}/databases/{database_id}/query",
                headers=headers,
                json=body,
                timeout=15,
            )
            if resp.status_code == 200:
                logger.info("Working filter: prop=%r type=%r value=%r", prop_name, prop_type, ready_value)
                return filter_clause
        except Exception:
            pass

    return None


def fetch_ready_tasks(database_id: str, token: str) -> List[Dict[str, Any]]:
    """
    Query Notion DB for pages whose status == the configured 'ready' value.
    The ready value is stored in Keychain as 'notion_ready_status'.
    """
    import httpx
    from core.config import get_secret

    # القيمة المُعدّة من الإعدادات، وإلا الافتراضية
    ready_value = get_secret("notion_ready_status") or STATUS_READY
    headers = _notion_headers(token)

    # ① اكتشف الـ filter الصحيح
    working_filter = _find_working_filter(database_id, headers, ready_value)
    if working_filter is None:
        # أظهر الخيارات الفعلية
        try:
            opts = get_status_options(database_id, token)
            hints = []
            for col, vals in opts.items():
                hints.append(f"'{col}': {vals}")
            hint_str = " | ".join(hints) if hints else "(تعذّر جلب الخيارات)"
        except Exception:
            hint_str = "(تعذّر جلب الخيارات)"
        raise ValueError(
            f"القيمة '{ready_value}' غير موجودة في عمود الحالة.\n"
            f"الخيارات المتاحة في قاعدتك: {hint_str}\n"
            f"اذهب إلى ⚙️ الإعدادات ← Notion ← اختر قيمة 'جاهز للنشر' الصحيحة."
        )

    # ② اجلب كل الصفحات مع الـ pagination
    tasks = []
    cursor = None

    while True:
        body: Dict[str, Any] = {"filter": working_filter}
        if cursor:
            body["start_cursor"] = cursor

        try:
            resp = httpx.post(
                f"{NOTION_BASE_URL}/databases/{database_id}/query",
                headers=headers,
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            response = resp.json()
        except Exception as e:
            logger.error("Notion query failed: %s", e)
            raise

        for page in response.get("results", []):
            try:
                tasks.append(_page_to_task(page))
            except Exception as e:
                logger.warning("Failed to parse page %s: %s", page.get("id"), e)

        if response.get("has_more"):
            cursor = response.get("next_cursor")
        else:
            break

    logger.info("Fetched %d ready tasks from Notion", len(tasks))
    return tasks


def list_databases(token: str) -> List[Dict[str, str]]:
    """
    Return all databases the integration can access.
    Uses search without filter (Notion API only allows "page"/"data_source"),
    then filters by object=="database" on our side.
    """
    client = _get_client(token)
    results = []
    cursor = None

    while True:
        kwargs: Dict[str, Any] = {"page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor

        try:
            response = client.search(**kwargs)
        except Exception as e:
            logger.error("Notion search failed: %s", e)
            raise

        for item in response.get("results", []):
            if item.get("object") != "database":
                continue
            title_parts = item.get("title", [])
            title = "".join(p.get("plain_text", "") for p in title_parts) or "(بدون عنوان)"
            db_id = item["id"].replace("-", "")
            results.append({"id": db_id, "title": title})

        if response.get("has_more"):
            cursor = response.get("next_cursor")
        else:
            break

    return results


def update_task_status(page_id: str, notion_status: str, token: str) -> bool:
    """
    Update the Status property of a Notion page.
    Tries both Arabic and English property names, and both 'status' and 'select' types.
    """
    import httpx

    headers = _notion_headers(token)

    for prop_name in ["الحالة", "Status"]:
        for prop_type in ["status", "select"]:
            try:
                payload: Dict[str, Any] = {
                    "properties": {
                        prop_name: {
                            prop_type: {"name": notion_status}
                        }
                    }
                }
                resp = httpx.patch(
                    f"{NOTION_BASE_URL}/pages/{page_id}",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
                logger.info("Updated Notion page %s → %s", page_id, notion_status)
                return True
            except Exception as e:
                logger.debug("update attempt (%s/%s) failed: %s", prop_name, prop_type, e)
                continue

    logger.error("All update attempts failed for page %s", page_id)
    return False


def test_connection(database_id: str, token: str) -> Dict[str, Any]:
    """
    Test Notion connectivity. Returns {'success': bool, 'message': str, 'db_title': str}.
    """
    import httpx

    try:
        headers = _notion_headers(token)
        resp = httpx.get(
            f"{NOTION_BASE_URL}/databases/{database_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        db = resp.json()
        title_parts = db.get("title", [])
        db_title = "".join(part.get("plain_text", "") for part in title_parts)
        return {"success": True, "message": "الاتصال ناجح", "db_title": db_title}
    except Exception as e:
        return {"success": False, "message": str(e), "db_title": ""}
