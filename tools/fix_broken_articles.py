"""enrich_zohar (побочный фикс) — починить 3 статьи с утёкшим в тело заголовком.

Дефект конвертации (предсуществующий): у vayera/005, vayechi/021, vayechi/082
пустые <title>/<h1>/og:title, а строка «# Статья N. Заголовок» утекла в <article>.
Из-за этого первый § (vayera/005 §76) не размечен para-start (нет якоря), {глава|N}
ведёт на статью без заголовка, а строка индекса — без названия.

Чинит детерминированно из самой утёкшей строки (восстанавливать нечего — данные на месте):
  • заполняет <title>/<h1>/og:title/twitter:title = «Статья N. Заголовок»;
  • вариант A (заголовок склеен с §): <p>﻿# … \nNN) … → <p class="para-start" id="pNN">NN) …;
  • вариант B (заголовок отдельным <p>): удаляет мусорный <p>﻿# …</p>;
  • срезает утёкший префикс из description/og/twitter;
  • правит строку этих статей в индексе главы (заголовок + §-диапазон).
Идемпотентно (непустой <title> → пропуск).

Запуск:  python tools/fix_broken_articles.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
TARGETS = ["vayera/005.html", "vayechi/021.html", "vayechi/082.html"]
HEAD_RX = re.compile(r"<p>﻿?#\s*Статья\s+(\d+)\.\s*([^<\n]+?)\s*(?:</p>|\n)")


def fix_index_row(slug: str, n: int, full_title: str) -> None:
    fp = ROOT / slug / "index.html"
    art = Z.parse_article(ROOT / slug / f"{n:03d}.html")
    rng = Z.fmt_range(art["para_start"], art["para_end"])
    lines = fp.read_text(encoding="utf-8").split("\n")
    href = f'{n:03d}.html'
    out = []
    for ln in lines:
        if f'href="{href}"' in ln:
            ln = ln.replace(f'<a href="{href}"></a>',
                            f'<a href="{href}">{full_title}</a>')
            ln = re.sub(r'<span class="status[^"]*">.*?</span>(?=</li>)',
                        f'<span class="status done">{rng}</span>', ln, count=1)
        out.append(ln)
    fp.write_text("\n".join(out), encoding="utf-8")


def main() -> int:
    fixed = 0
    for rel in TARGETS:
        fp = ROOT / rel
        text = fp.read_text(encoding="utf-8")
        if "<title></title>" not in text:
            print(f"  {rel}: уже починен, пропуск")
            continue
        m = HEAD_RX.search(text)
        if not m:
            print(f"  {rel}: утёкший заголовок не найден — пропуск", file=sys.stderr)
            continue
        n = int(m.group(1))
        title_text = m.group(2).strip()
        full = f"Статья {n}. {title_text}"

        # head-метаданные
        text = text.replace("<title></title>", f"<title>{full}</title>", 1)
        text = text.replace('property="og:title" content=""',
                            f'property="og:title" content="{full}"', 1)
        text = text.replace('name="twitter:title" content=""',
                            f'name="twitter:title" content="{full}"', 1)
        text = re.sub(r"(<h1[^>]*>)</h1>", rf"\g<1>{full}</h1>", text, count=1)

        # тело: вариант B (отдельный <p>) — удалить; вариант A (склейка) — разметить §
        text = re.sub(r"<p>﻿?#[^\n]*?</p>\n?", "", text, count=1)
        text = re.sub(r"<p>﻿?#[^\n]*\n(\d+)\)",
                      r'<p class="para-start" id="p\1">\1)', text, count=1)

        # description/og/twitter — срезать утёкший префикс «﻿# Статья N. Заголовок »
        text = text.replace(f"﻿# {full} ", "")

        fp.write_text(text, encoding="utf-8")
        slug = rel.split("/")[0]
        fix_index_row(slug, n, full)
        print(f"  {rel}: → «{full}», §{Z.parse_article(fp)['para_start']}–"
              f"{Z.parse_article(fp)['para_end']}")
        fixed += 1
    print(f"Починено статей: {fixed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
