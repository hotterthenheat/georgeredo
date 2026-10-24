#!/usr/bin/env python3
"""render_final.py — COMPASS_FINAL_REPORT.md → COMPASS_FINAL_REPORT.pdf, the same way as FINAL REPORT/build/render.py: pandoc
writes one self-contained HTML page and headless Chromium prints it (A4 landscape, the same stylesheet)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'FINAL REPORT' / 'build'))
import render as R  # noqa: E402  (its CSS and Chromium path)

WORK = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/compass_final/render')


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    css = WORK / 'report.css'
    css.write_text(R.CSS)
    html = WORK / 'COMPASS_FINAL_REPORT.html'
    subprocess.run(['pandoc', str(HERE / 'COMPASS_FINAL_REPORT.md'), '-f',
                    'markdown+pipe_tables-yaml_metadata_block-tex_math_dollars-implicit_figures', '-t', 'html5', '--standalone',
                    '--embed-resources', f'--resource-path={HERE}', '--css', str(css),
                    '--metadata', 'pagetitle=Compass Final', '-o', str(html)], check=True)
    pdf = HERE / 'COMPASS_FINAL_REPORT.pdf'
    subprocess.run([R.CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                    f'--print-to-pdf={pdf}', f'file://{html}'], check=True, capture_output=True)
    print('wrote', pdf, pdf.stat().st_size)


if __name__ == '__main__':
    main()
