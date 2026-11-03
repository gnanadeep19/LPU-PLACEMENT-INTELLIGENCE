"""Render docs/VIVA_QA.md to a print-ready PDF using headless Chrome."""

from __future__ import annotations

import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "VIVA_QA.md"
OUTPUT = ROOT / "docs" / "LPU_Placement_Intelligence_Viva_QA.pdf"
HTML_OUT = ROOT / "reports" / "presentation" / "viva.html"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]

CSS = """
@page { size: A4; margin: 14mm 15mm 13mm 15mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 10pt; line-height: 1.48; color: #1f2933; margin: 0;
}
.cover {
  border-left: 6px solid #0f766e; padding: 4px 0 4px 16px; margin-bottom: 18px;
}
.cover .kicker {
  font-size: 9pt; letter-spacing: 2.4px; text-transform: uppercase;
  color: #0f766e; font-weight: 700; margin: 0 0 6px;
}
.cover h1 { font-size: 26pt; line-height: 1.1; margin: 0 0 6px; color: #0b1f2a; }
.cover .platform { font-size: 13pt; font-weight: 600; color: #334e5c; margin: 0 0 10px; }
.cover p { margin: 0; font-size: 9.2pt; color: #52616b; max-width: 165mm; }
h2 {
  font-size: 12.5pt; color: #0b1f2a; margin: 15px 0 7px;
  padding-bottom: 4px; border-bottom: 1.6px solid #0f766e;
  break-after: avoid; page-break-after: avoid;
}
.qa { break-inside: avoid; page-break-inside: avoid; margin: 0 0 7px; padding: 0 0 0 11px;
      border-left: 2px solid #cfe3e0; }
.qa h3 {
  font-size: 10.4pt; margin: 0 0 2px; color: #0f4c5c; font-weight: 700; line-height: 1.35;
}
.qa h3 .num { color: #0f766e; }
.qa p { margin: 0 0 2px; text-align: justify; }
p { margin: 0 0 8px; }
code {
  font-family: "Cascadia Mono", Consolas, monospace; font-size: 8.8pt;
  background: #eef4f3; color: #0b4f4a; padding: 0 3px; border-radius: 2px;
}
table { width: 100%; border-collapse: collapse; margin: 6px 0 14px; font-size: 9.4pt;
        break-inside: avoid; page-break-inside: avoid; }
th { background: #0f766e; color: #ffffff; text-align: left; padding: 6px 8px; font-weight: 600; }
td { padding: 5px 8px; border-bottom: 1px solid #dbe6e5; }
tr:nth-child(even) td { background: #f6faf9; }
td:first-child { font-weight: 600; color: #0b1f2a; white-space: nowrap; }
ul { margin: 4px 0 10px; padding-left: 18px; }
li { margin-bottom: 3px; }
.tip { background: #f2f8f6; border: 1px solid #cfe3e0; border-left: 4px solid #0f766e;
       padding: 9px 12px; border-radius: 3px; break-inside: avoid; page-break-inside: avoid; }
"""


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def parse(markdown: str):
    blocks = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                raw = lines[index].strip().strip("|")
                cells = [cell.strip() for cell in raw.split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                    rows.append(cells)
                index += 1
            blocks.append(("table", rows))
            continue
        if stripped.startswith("# "):
            blocks.append(("h1", stripped[2:].strip()))
        elif stripped.startswith("## "):
            blocks.append(("h2", stripped[3:].strip()))
        elif stripped.startswith("### "):
            blocks.append(("h3", stripped[4:].strip()))
        elif stripped.startswith("- "):
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(lines[index].strip()[2:].strip())
                index += 1
            blocks.append(("ul", items))
            continue
        else:
            paragraph = [stripped]
            index += 1
            while index < len(lines):
                nxt = lines[index].strip()
                if not nxt or nxt.startswith(("#", "|", "- ")):
                    break
                paragraph.append(nxt)
                index += 1
            blocks.append(("p", " ".join(paragraph)))
            continue
        index += 1
    return blocks


def render(blocks) -> str:
    title = next(block[1] for block in blocks if block[0] == "h1")
    subtitle = next(block[1] for block in blocks if block[0] == "h2")
    intro = next(block[1] for block in blocks if block[0] == "p")

    body = []
    closed = True
    for kind, value in blocks:
        if kind == "h1" or (kind == "h2" and value == subtitle) or (kind == "p" and value == intro):
            continue
        if kind == "h3":
            if not closed:
                body.append("</section>")
            match = re.match(r"(\d+)\.\s*(.*)", value)
            number, question = (match.group(1), match.group(2)) if match else ("", value)
            heading = f'<span class="num">{number}.</span> {inline(question)}' if number else inline(question)
            body.append(f'<section class="qa"><h3>{heading}</h3>')
            closed = False
        elif kind == "h2":
            if not closed:
                body.append("</section>")
                closed = True
            body.append(f"<h2>{inline(value)}</h2>")
        elif kind == "p":
            text = inline(value)
            css = "tip" if value.startswith("Open with") else ""
            body.append(f'<p class="{css}">{text}</p>' if css else f"<p>{text}</p>")
        elif kind == "ul":
            items = "".join(f"<li>{inline(item)}</li>" for item in value)
            body.append(f"<ul>{items}</ul>")
        elif kind == "table":
            head, *rest = value
            head_html = "".join(f"<th>{inline(cell)}</th>" for cell in head)
            rows_html = "".join(
                "<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in rest
            )
            body.append(f"<table><thead><tr>{head_html}</tr></thead><tbody>{rows_html}</tbody></table>")
    if not closed:
        body.append("</section>")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<header class="cover">
  <p class="kicker">{html.escape(title)}</p>
  <h1>Viva Preparation</h1>
  <p class="platform">{html.escape(subtitle)}</p>
  <p>{inline(intro)}</p>
</header>
{chr(10).join(body)}
</body></html>"""


def main() -> int:
    blocks = parse(SOURCE.read_text(encoding="utf-8"))
    document = render(blocks)
    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(document, encoding="utf-8")

    chrome = next((path for path in CHROME_CANDIDATES if path.exists()), None)
    if chrome is None:
        print("No Chrome or Edge binary found for PDF rendering.", file=sys.stderr)
        return 1

    OUTPUT.unlink(missing_ok=True)
    result = subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            "--virtual-time-budget=3000",
            f"--print-to-pdf={OUTPUT}",
            HTML_OUT.resolve().as_uri(),
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if not OUTPUT.exists():
        print(result.stdout, result.stderr, file=sys.stderr)
        return 1

    data = OUTPUT.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    print(f"PDF: {OUTPUT}")
    print(f"Size: {len(data) / 1024:.0f} KB, pages: {pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
