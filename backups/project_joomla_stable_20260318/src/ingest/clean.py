from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass
class CleanResult:
    title: str
    text: str


import lxml.html

def clean_html_to_text(html_content: str) -> CleanResult:
    if not html_content:
        return CleanResult(title="", text="")
        
    # Use lxml for speed
    try:
        # Check if it's bytes or str
        if isinstance(html_content, bytes):
            # lxml parses bytes better if encoding declared, but usually ok
            pass
            
        tree = lxml.html.fromstring(html_content)
    except Exception:
        # Fallback or return empty
        return CleanResult(title="", text="")
    
    # Phase 125: Strict Body Selection
    body_selectors = [
        "div[itemprop='articleBody']",
        "div.com-content-article__body",
        "div.articleBody", 
        "div[itemprop='text']",
        "div.main-both",
        "article", 
        "main"
    ]
    
    target_node = None
    for selector in body_selectors:
        # lxml cssselect requires 'cssselect' package usually, or use xpath
        # cssselect might not be installed. Use XPath equivalent or simplified.
        # Actually lxml.html has .cssselect method if cssselect is installed.
        # Check standard env. If not sure, use generic xpath?
        # Let's try .cssselect, but wrap in try?
        # Benchmark script used cssselect and it worked (initially?) 
        # Wait, benchmark failed on 'bs4'. It didn't reach lxml part.
        # If cssselect is missing, lxml throws error.
        # Safer to use pure lxml xpath if possible, OR assume cssselect is there (it is common).
        # Let's use generic xpath for simplicity and speed.
        
        # Mapping simple selectors to xpath (approx)
        if "itemprop" in selector:
            # div[itemprop='articleBody'] -> //div[@itemprop='articleBody']
            attr, val = selector.split('[')[1].split(']')[0].split('=')
            val = val.strip("'\"")
            xpath = f".//div[@{attr}='{val}']"
        elif "." in selector:
            # div.class -> //div[contains(concat(' ', normalize-space(@class), ' '), ' class ')]
            tag, cls = selector.split('.')
            xpath = f".//{tag}[contains(concat(' ', normalize-space(@class), ' '), ' {cls} ')]"
        else:
            xpath = f".//{selector}"
            
        found = tree.xpath(xpath)
        if found:
            # Pick first large one
            for node in found:
                if len(node.text_content()) > 50:
                    target_node = node
                    break
            if target_node is not None:
                break

    if target_node is not None:
        root = target_node
    else:
        root = tree
        
    # Remove unwanted tags
    # .//script | .//style ...
    for tag in root.xpath('.//script|.//style|.//meta|.//noscript|.//iframe|.//header|.//footer|.//nav'):
        tag.drop_tree()

    # Extract Title (from original tree, not body)
    title = ""
    try:
        t_node = tree.find(".//title")
        if t_node is not None:
            title = t_node.text_content().strip()
    except:
        pass

    text = root.text_content()
    
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Collapse multiple spaces
    text = re.sub(r'[ \t]+', ' ', text)

    return CleanResult(title=title, text=text)
