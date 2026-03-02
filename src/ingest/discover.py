from __future__ import annotations

from urllib.parse import urljoin, urlparse
from typing import List, Set

from bs4 import BeautifulSoup


def is_same_domain(url: str, allowed_domain: str) -> bool:
    host = urlparse(url).netloc
    return host == allowed_domain


def extract_links(base_url: str, html: str, allowed_domain: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links: Set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue

        abs_url = urljoin(base_url, href)
        # drop fragments
        parsed = urlparse(abs_url)
        abs_url = parsed._replace(fragment="").geturl()

        if is_same_domain(abs_url, allowed_domain):
            links.add(abs_url)

    return sorted(links)
