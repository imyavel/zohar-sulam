"""enrich_zohar (уточнение) — вернуть «(Вначале)» в имя глав Берешита.

«Берешит 1» / «Берешит 2» → «Берешит 1 (Вначале)» / «Берешит 2 (Вначале)» — но
ТОЛЬКО как имя главы (крошка, мета-строка, JSON-LD name, title/h1/og/description
индекса, строка в kniga-bereshit). Цитаты Торы в теле перевода вида «(Берешит 1:26)»
(= Бытие гл. 1) НЕ трогаются — отсюда привязка к точным разделителям, а не голый
«Берешит N». Идемпотентно (вставка « (Вначале)» рвёт требуемый разделитель).

  python tools/add_bereshit_subtitle.py
"""
from __future__ import annotations
import re
import sys
import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
SUB = r"Берешит \1 (Вначале)"
# (regex, replacement) — имя главы «Берешит N» только в этих контекстах:
RULES = [
    (re.compile(r"Берешит ([12])</a>"), SUB + "</a>"),                    # крошка / строка книги
    (re.compile(r"Берешит ([12]) · Сулам"), SUB + " · Сулам"),           # мета-строка статьи
    (re.compile(r'"name":"Берешит ([12])"'), r'"name":"Берешит \1 (Вначале)"'),  # JSON-LD name
    (re.compile(r"<title>Берешит ([12])</title>"), "<title>" + SUB + "</title>"),
    (re.compile(r'content="Берешит ([12])"'), 'content="' + SUB + '"'),  # og/twitter title
    (re.compile(r'content="Берешит ([12]) — '), 'content="' + SUB + " — "),  # description
    (re.compile(r"<h1>Берешит ([12])</h1>"), "<h1>" + SUB + "</h1>"),    # h1 индекса
    (re.compile(r"›</span>Берешит ([12])</div>"), "›</span>" + SUB + "</div>"),  # крошка-хвост индекса
]


def main() -> int:
    files = (glob.glob(str(ROOT / "bereshit-1" / "*.html"))
             + glob.glob(str(ROOT / "bereshit-2" / "*.html"))
             + [str(ROOT / "kniga-bereshit" / "index.html")])
    total = 0
    touched = 0
    for fp in files:
        p = Path(fp)
        t = p.read_text(encoding="utf-8")
        n = 0
        for rx, rep in RULES:
            t, k = rx.subn(rep, t)
            n += k
        if n:
            p.write_text(t, encoding="utf-8")
            touched += 1
            total += n
    print(f"Заменено вхождений имени главы: {total} в {touched} файлах.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
