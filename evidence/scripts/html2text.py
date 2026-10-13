import re, html, sys, os, pathlib
src = pathlib.Path(sys.argv[1]); dst = pathlib.Path(sys.argv[2]); dst.mkdir(parents=True, exist_ok=True)
for f in sorted(src.glob('*.html')):
    s = f.read_text(encoding='utf-8', errors='replace')
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<style.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<(br|/p|/div|/h[1-6]|/li|/tr|/section|/article|/header|/footer|/td|/th)[^>]*>', '\n', s, flags=re.I)
    t = re.sub(r'<[^>]+>', ' ', s)
    t = html.unescape(t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    out = dst / (f.stem + '.txt')
    out.write_text(t.strip(), encoding='utf-8')
    print(f"{f.name}: {len(t)} chars -> {out.name}")
