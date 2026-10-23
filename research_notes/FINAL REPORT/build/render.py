#!/usr/bin/env python3
"""render.py — FINAL_RESEARCH_REPORT.md → FINAL_RESEARCH_REPORT.pdf: pandoc (3.1) writes one self-contained HTML page
with the charts embedded, and headless Chromium prints it (A4 landscape, small type so the tables fit the page)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
WORK = Path('/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/fr')
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

CSS = """
@page { size: A4 landscape; margin: 11mm 10mm 12mm 10mm; }
body { font-family: 'DejaVu Sans', Helvetica, Arial, sans-serif; font-size: 8.6pt; line-height: 1.32; color: #111; max-width: none; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 6pt 0; }
h2 { font-size: 12pt; margin: 14pt 0 4pt 0; border-bottom: 1px solid #bbb; padding-bottom: 2pt; page-break-after: avoid; }
h1 + p, h2 + p { page-break-before: avoid; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 8pt 0; font-size: 6.9pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 0.5px solid #c8c8c8; padding: 1.4pt 3pt; vertical-align: top; }
th { background: #eef2f7; text-align: left; }
tbody tr:nth-child(even) { background: #fafafa; }
td { word-break: break-word; }
img { max-width: 92%; display: block; margin: 4pt auto 6pt auto; page-break-inside: avoid; }
code { font-size: 7.6pt; background: #f3f3f3; padding: 0 2px; }
blockquote { border-left: 3px solid #c0504d; margin: 4pt 0; padding: 2pt 8pt; background: #fbeeee; }
.part { page-break-before: always; }
h1.part-title { page-break-before: always; font-size: 15pt; }
"""


def main():
    md = OUT / 'FINAL_RESEARCH_REPORT.md'
    css = WORK / 'report.css'
    css.write_text(CSS)
    html = WORK / 'FINAL_RESEARCH_REPORT.html'
    # every section starts on a new page (h2 "## #"), and each Part heading too
    src = md.read_text()
    src = src.replace('\n# Part ', '\n<div style="page-break-before: always"></div>\n\n# Part ')
    src = src.replace('\n## #', '\n<div style="page-break-before: always"></div>\n\n## #')
    tmp = WORK / 'report_src.md'
    tmp.write_text(src)
    subprocess.run(['pandoc', str(tmp), '-f', 'markdown+pipe_tables-yaml_metadata_block-tex_math_dollars-implicit_figures', '-t', 'html5', '--standalone',
                    '--embed-resources', f'--resource-path={OUT}', '--css', str(css), 
                    '--metadata', 'pagetitle=Final research report', '-o', str(html)], check=True)
    pdf = OUT / 'FINAL_RESEARCH_REPORT.pdf'
    subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                    f'--print-to-pdf={pdf}', f'file://{html}'], check=True, capture_output=True)
    print('wrote', pdf, pdf.stat().st_size)


if __name__ == '__main__':
    main()
