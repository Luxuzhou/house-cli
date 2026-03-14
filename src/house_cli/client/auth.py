"""Browser cookie extraction and credential management.

Cookie resolution order:
1. Manual cookie file ~/.config/house-cli/cookies.json (fastest, user-controlled)
2. browser-cookie3 library extraction from Chrome/Edge/Firefox (automatic)
3. Fallback: empty dict (caller handles gracefully)

Cookie file format (cookies.json):
{
    "ke.com": {
        "lianjia_uuid": "xxx",
        "lianjia_ssid": "xxx",
        ...
    }
}
"""

import json
import logging
import os
import stat
import time

log = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "house-cli",
)
COOKIE_FILE = os.path.join(CONFIG_DIR, "cookies.json")
COOKIE_TTL = 7 * 24 * 3600  # 7 days


def _load_cookie_file() -> dict:
    """Load cookies from the manual cookie file."""
    if not os.path.exists(COOKIE_FILE):
        return {}
    try:
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_cookies(domain: str, cookies: dict):
    """Save cookies for a domain to the cookie file with restricted permissions."""
    data = _load_cookie_file()
    data[domain] = {
        "_updated_at": int(time.time()),
        **cookies,
    }
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # Set 0o600 permissions (owner read/write only)
    try:
        os.chmod(COOKIE_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # Windows may not support chmod fully


def get_cookies(domain: str) -> dict:
    """Get cookies for a domain. Returns empty dict if none or expired."""
    data = _load_cookie_file()
    entry = data.get(domain, {})
    if not entry:
        return {}
    updated = entry.get("_updated_at", 0)
    if time.time() - updated > COOKIE_TTL:
        return {}
    # Strip internal keys
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def _try_browser_cookie3(domain: str) -> dict:
    """Extract cookies using browser-cookie3 library.

    Tries Chrome, then Edge, then Firefox.
    Works even when the browser is running on most platforms.
    """
    try:
        import browser_cookie3
    except ImportError:
        return {}

    browsers = [
        ("chrome", browser_cookie3.chrome),
        ("edge", browser_cookie3.edge),
        ("firefox", browser_cookie3.firefox),
    ]

    for name, loader in browsers:
        try:
            cj = loader(domain_name=f".{domain}")
            cookies = {c.name: c.value for c in cj if domain in c.domain}
            if cookies:
                log.debug("Extracted %d cookies from %s for %s", len(cookies), name, domain)
                return cookies
        except Exception:
            continue

    return {}


def load_or_extract_cookies(domain: str) -> dict:
    """Load cookies from file, or try browser extraction as fallback.

    Resolution order:
    1. Manual cookie file (if present and not expired)
    2. browser-cookie3 extraction (auto-saved on success)
    """
    cookies = get_cookies(domain)
    if cookies:
        return cookies

    # Try browser-cookie3
    cookies = _try_browser_cookie3(domain)
    if cookies:
        save_cookies(domain, cookies)
        return cookies

    return {}
