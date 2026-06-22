"""Render MircoVerse markdown docs to shareable PDFs.

Pipeline: markdown -> styled HTML (code/diagram blocks preserved via fenced_code +
codehilite) -> Chrome headless --print-to-pdf. No pandoc/latex needed. Diagrams in the
docs are ASCII/code fences, so they render faithfully in monospace.

Usage:
    .venv/Scripts/python.exe scripts/make_pdf.py                 # all default docs
    .venv/Scripts/python.exe scripts/make_pdf.py World.md QUICKSTART.md
Output: dist/pdf/<name>.pdf
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import markdown

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "dist" / "pdf"

DEFAULT_DOCS = [
    "World.md",
    "Architecture.md",
    "Protocol.md",
    "QUICKSTART.md",
]

# Editorial / research-paper styling — matches the project's locked aesthetic:
# Newsreader-ish serif body, mono for code/diagrams, warm-charcoal ink, restrained amber.
CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "Newsreader", Georgia, "Times New Roman", serif;
  font-size: 10.5pt; line-height: 1.5; color: #23211e; max-width: 100%;
}
h1, h2, h3, h4 { font-family: "Inter", -apple-system, "Segoe UI", sans-serif;
  color: #1a1815; line-height: 1.25; margin: 1.3em 0 0.5em; font-weight: 600; }
h1 { font-size: 21pt; border-bottom: 2px solid #c8862a; padding-bottom: 0.25em; }
h2 { font-size: 15pt; border-bottom: 1px solid #ddd6c9; padding-bottom: 0.2em; margin-top: 1.6em; }
h3 { font-size: 12pt; }
h4 { font-size: 10.5pt; color: #5a554c; }
a { color: #a8701f; text-decoration: none; }
p, li { orphans: 2; widows: 2; }
blockquote { margin: 0.8em 0; padding: 0.4em 1em; border-left: 3px solid #c8862a;
  background: #faf7f1; color: #4a463e; }
code { font-family: "JetBrains Mono", "Consolas", monospace; font-size: 8.6pt;
  background: #f3efe7; padding: 0.1em 0.3em; border-radius: 3px; }
pre { font-family: "JetBrains Mono", "Consolas", monospace; font-size: 8.2pt;
  background: #1c1a17; color: #e8e3d8; padding: 0.9em 1.1em; border-radius: 6px;
  overflow-x: auto; line-height: 1.35; page-break-inside: avoid; white-space: pre; }
pre code { background: none; padding: 0; color: inherit; font-size: inherit; }
/* ASCII diagrams + tables shouldn't split across pages where avoidable */
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 0.8em 0;
  page-break-inside: avoid; }
th, td { border: 1px solid #ddd6c9; padding: 0.35em 0.55em; text-align: left; vertical-align: top; }
th { background: #f3efe7; font-family: "Inter", sans-serif; font-weight: 600; }
hr { border: none; border-top: 1px solid #ddd6c9; margin: 1.5em 0; }
img { max-width: 100%; }
.doc-footer { margin-top: 2em; padding-top: 0.6em; border-top: 1px solid #ddd6c9;
  font-size: 8pt; color: #8a8478; font-family: "Inter", sans-serif; }
/* Pygments code highlighting (codehilite) — muted on dark */
.codehilite .k, .codehilite .kd, .codehilite .kn { color: #d9a441; }
.codehilite .s, .codehilite .s1, .codehilite .s2 { color: #9ec98a; }
.codehilite .c, .codehilite .c1, .codehilite .cm { color: #7d776a; font-style: italic; }
.codehilite .nf, .codehilite .nc { color: #6fb3d6; }
.codehilite .mi, .codehilite .mf { color: #d98a6f; }
"""

HTML_TMPL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{title}</title><style>{css}</style></head>
<body>{body}
<div class="doc-footer">MircoVerse — {title} · generated from {src}</div>
</body></html>"""


def find_chrome() -> str | None:
    for c in (
        "chrome", "google-chrome", "chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ):
        if shutil.which(c) or Path(c).exists():
            return c
    return None


def render_html(md_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["fenced_code", "codehilite", "tables", "toc", "sane_lists"],
        extension_configs={"codehilite": {"guess_lang": False, "noclasses": False}},
    )
    html = HTML_TMPL.format(title=md_path.stem, css=CSS, body=body, src=md_path.name)
    out_html = OUT / f"{md_path.stem}.html"
    out_html.write_text(html, encoding="utf-8")
    return out_html


def html_to_pdf(chrome: str, html_path: Path) -> Path:
    pdf_path = OUT / f"{html_path.stem}.pdf"
    url = html_path.resolve().as_uri()
    subprocess.run(
        [
            chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}", url,
        ],
        check=True, capture_output=True,
    )
    return pdf_path


def main(argv: list[str]) -> int:
    docs = argv[1:] or DEFAULT_DOCS
    OUT.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    if not chrome:
        print("ERROR: no Chrome/Edge found for headless PDF printing.", file=sys.stderr)
        return 2

    made = []
    for name in docs:
        md_path = REPO / name
        if not md_path.exists():
            print(f"skip (not found): {name}", file=sys.stderr)
            continue
        html = render_html(md_path)
        pdf = html_to_pdf(chrome, html)
        size_kb = pdf.stat().st_size // 1024
        print(f"OK  {name:18s} -> {pdf.relative_to(REPO)}  ({size_kb} KB)")
        made.append(pdf)

    print(f"\n{len(made)} PDF(s) in {OUT.relative_to(REPO)}")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
