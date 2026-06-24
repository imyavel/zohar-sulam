"""enrich_zohar (§2.0 deploy) — пересобрать sitemap.xml репо zohar-sulam.

После split (bereshit→bereshit-1/2) старые URL `bereshit/*` исчезли. Регенерируем
карту из текущего дерева: root + kniga-*/ + глава/ + глава/NNN.html. Формат — как был
(`<url><loc>…</loc><lastmod>…</lastmod></url>`). lastmod передаётся аргументом (CLAUDE.md:
без угадывания даты), по умолчанию — последняя сборка статей.

  python tools/build_sitemap.py 2026-06-24
"""
from __future__ import annotations
import sys
import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
BASE = "https://imyavel.github.io/zohar-sulam"


def main() -> int:
    lastmod = sys.argv[1] if len(sys.argv) > 1 else "2026-06-02"
    urls = [f"{BASE}/"]
    for kn in sorted(p.name for p in ROOT.iterdir()
                     if p.is_dir() and p.name.startswith("kniga-")):
        urls.append(f"{BASE}/{kn}/")
    for slug in Z.chapter_dirs():
        for fp in sorted(glob.glob(str(ROOT / slug / "[0-9][0-9][0-9].html"))):
            urls.append(f"{BASE}/{slug}/{Path(fp).name}")
        urls.append(f"{BASE}/{slug}/")

    body = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>" for u in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}\n</urlset>\n")
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"sitemap.xml: {len(urls)} URL (lastmod {lastmod})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
