from bs4 import BeautifulSoup

# ==============================================================================
# Logic mirrored from src/ingest/clean.py (clean_html_to_text) - SIMPLIFIED
# ==============================================================================
def simple_clean(html):
    soup = BeautifulSoup(html, "html.parser")
    # clean.py: line 88 -> drops script, style, meta, noscript, iframe, header, footer, nav
    for tag in soup.find_all(["script", "style", "meta", "noscript", "iframe", "header", "footer", "nav"]):
        tag.decompose()
    
    # clean.py attempts to find article body, but falls back to root.
    # We will assume body selection or root cleaning for this raw example.
    return soup.get_text("\n", strip=True)

# ==============================================================================
# Logic mirrored from src/ingest/process_one.py (extract_text_with_tables)
# ==============================================================================
def table_clean(html):
    soup = BeautifulSoup(html, "html.parser")
    lines = []
    # process_one.py: line 145 -> iterates tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            # process_one.py: line 147 -> gets text from th/td
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
            if cells:
                # process_one.py: line 149 -> joins with " | "
                lines.append(" | ".join(cells))
    return "\n".join(lines)


html_boilerplate = """
<html>
<body>
<header><nav>Menu: Home | About</nav></header>
<div class="articleBody">
    <h1>Security Policy 2024</h1>
    <p>Employees must change passwords every 90 days.</p>
</div>
<footer>Copyright 2024</footer>
</body>
</html>
"""

html_table = """
<html>
<body>
<div class="articleBody">
    <table>
        <tr><th>Department</th><th>Hotline</th></tr>
        <tr><td>IT Support</td><td>1100</td></tr>
        <tr><td>HR</td><td>2200</td></tr>
    </table>
</div>
</body>
</html>
"""

print("--- Example 1: Boilerplate Removal (Actual Output) ---")
print(f"After (Cleaned): \n{simple_clean(html_boilerplate)}")

print("\n--- Example 2: Table Structure (Actual Output) ---")
print(f"After (Cleaned): \n{table_clean(html_table)}")
