from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path

import requests


@dataclass
class FetchResult:
    url: str
    status_code: int
    html: str
    content_type: str
    fetched_at: float
    error: str = ""  # ✅ เพิ่ม: เก็บ error เผื่อ debug


def fetch_url(
    url: str,
    timeout_sec: int = 20,
    headers: Optional[Dict[str, str]] = None
) -> FetchResult:
    hdrs = {
        "User-Agent": "rag-web-crawler/0.1 (+internal-prototype)",
        "Accept": "text/html,application/xhtml+xml",
    }
    if headers:
        hdrs.update(headers)

    try:
        r = requests.get(url, headers=hdrs, timeout=timeout_sec)
        ct = r.headers.get("Content-Type", "")

        html = ""
        if r.ok:
            # Decode robustly: use requests' best guess (apparent_encoding) when charset not provided
            r.encoding = r.apparent_encoding or "utf-8"
            html = r.text

        # --------------------------------------------------
        # Login Page Detection
        # --------------------------------------------------
        # If login detected, return a placeholder page so RAG can answer "You need to login at..."
        final_url = r.url.lower()
        
        is_auth = False
        auth_reason = ""

        # 1. Check URL redirect to login
        if any(x in final_url for x in ["login", "signin", "auth", "sso"]):
            is_auth = True
            auth_reason = "redirect_to_login"

        # 2. Check HTML content for password field
        elif "type=\"password\"" in html.lower() or "type='password'" in html.lower():
            is_auth = True
            auth_reason = "password_field_found"

        if is_auth:
            # Extract potential resource name from URL for better RAG context
            # e.g. http://.../smc -> smc
            path_parts = [p for p in r.url.split("/") if p and p not in ["http:", "https:", "www"]]
            resource_name = path_parts[-1] if path_parts else "Protected Resource"
            
            # Create synthetic HTML
            synthetic_html = (
                f"<html><head><title>Login to {resource_name} (Authentication Required)</title></head>"
                f"<body>"
                f"<h1>Access to {resource_name}</h1>"
                f"<p>The URL for <b>{resource_name}</b> is: <b>{url}</b></p>"
                f"<p>This page requires authentication.</p>"
                f"<p>Please <a href=\"{url}\">click here to login</a> to access {resource_name}.</p>"
                f"<!-- detected_by: {auth_reason} -->"
                f"</body></html>"
            )
            return FetchResult(
                url=url,
                status_code=200,   # Return 200 so it gets indexed
                html=synthetic_html,
                content_type="text/html",
                fetched_at=time.time(),
                error="",         # No error, treated as valid content
            )

        return FetchResult(
            url=url,
            status_code=int(r.status_code),
            html=html,
            content_type=ct,
            fetched_at=time.time(),
            error="",
        )

    except requests.exceptions.ReadTimeout:
        return FetchResult(
            url=url,
            status_code=0,
            html="",
            content_type="",
            fetched_at=time.time(),
            error=f"read_timeout(timeout_sec={timeout_sec})",
        )

    except requests.exceptions.ConnectTimeout:
        return FetchResult(
            url=url,
            status_code=0,
            html="",
            content_type="",
            fetched_at=time.time(),
            error=f"connect_timeout(timeout_sec={timeout_sec})",
        )

    except requests.exceptions.ConnectionError as e:
        return FetchResult(
            url=url,
            status_code=0,
            html="",
            content_type="",
            fetched_at=time.time(),
            error=f"connection_error({e})",
        )

    except Exception as e:
        return FetchResult(
            url=url,
            status_code=0,
            html="",
            content_type="",
            fetched_at=time.time(),
            error=f"error({e})",
        )



@dataclass
class DomainPolicy:
    ALLOWED_DOMAINS = [
        "localhost", "127.0.0.1", "10.", "192.168.", "172.16.", "nt.com", ".nt.com"
    ]
    DENIED_DOMAINS = [
        "whatismyipaddress.com", "doubleclick.net", "google-analytics.com", "facebook.com"
    ]

    @staticmethod
    def is_safe(url: str) -> bool:
        """
        Check if URL is safe to fetch based on internal policy.
        """
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            
            # 1. Deny List
            if any(d in hostname for d in DomainPolicy.DENIED_DOMAINS):
                return False
                
            # 2. Allow List (Logic: If internal-only mode is strict, this would be restrictive)
            # For now, we allows standard fetching but prioritize internal checks
            # or maybe the user wants STRICT allowlist? 
            # "Allowlist specific domains... or Denylist external"
            # Let's start with a flexible approach: Allow unless denied, but treat external as 'risky' (short timeout)
            return True
        except:
            return False

    @staticmethod
    def get_timeout(url: str) -> int:
        """
        Return strict timeout based on domain type.
        Internal: 15s
        External: 5s (Fail Fast)
        """
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            
            is_internal = any(d in hostname for d in DomainPolicy.ALLOWED_DOMAINS)
            return 15 if is_internal else 5
        except:
            return 5

def fetch_with_policy(url: str) -> FetchResult:
    """
    Wrapper around fetch_url that applies DomainPolicy.
    """
    if not DomainPolicy.is_safe(url):
        return FetchResult(
            url=url,
            status_code=403,
            html="",
            content_type="",
            fetched_at=time.time(),
            error="blocked_by_domain_policy"
        )
        
    timeout = DomainPolicy.get_timeout(url)
    return fetch_url(url, timeout_sec=timeout)

def save_raw_html(out_dir: str, url: str, html: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # (2.1) แก้ชื่อไฟล์: replace ":" -> "_"
    # --------------------------------------------------
    safe_name = (
        url.replace("https://", "")
        .replace("http://", "")
        .replace(":", "_")
        .replace("/", "_")
        .replace("?", "_")
        .replace("&", "_")
        .replace("=", "_")
        .strip("_")
    )

    # --------------------------------------------------
    # (2.2) กันนามสกุล .html ซ้ำ
    # --------------------------------------------------
    filename = safe_name if safe_name.endswith(".html") else f"{safe_name}.html"
    path = Path(out_dir) / filename

    path.write_text(html, encoding="utf-8")
    return str(path)

