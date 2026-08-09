"""Пересобрать списки главной страницы (index.html) по фактическому составу репо.

  * `const ARTICLES = [...]` — пул кнопки «Мне повезет!». Порядок глав берётся из
    книг-справочников `kniga-*/index.html` (канонический порядок Зоара), внутри
    главы — по номеру файла. Так список переживает split/merge глав.
  * `const INFO = {...}` — ссылки виджета недельной главы. Не переписывается,
    только проверяется: каждый непустой url должен указывать на существующий файл.

Запуск:  python tools/refresh_home_lists.py          (из корня репо zohar-sulam)
         python tools/refresh_home_lists.py --check  (только проверка, без записи)
Идемпотентно: повторный запуск не меняет файл.
"""
from __future__ import annotations
import glob
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
# Порядок книг Зоара (в самих kniga-*/index.html он не записан).
KNIGI = ["kniga-akdama", "kniga-bereshit", "kniga-shemot",
         "kniga-vayikra", "kniga-bamidbar", "kniga-devarim"]
CHAP_RX = re.compile(r'href="\.\./([a-z0-9-]+)/index\.html"')
ARTICLES_RX = re.compile(r"(const ARTICLES = \[)(.*?)(\];)", re.S)
INFO_RX = re.compile(r"const INFO = (\{.*?\});", re.S)


def chapter_order() -> list[str]:
    """Слаги глав в каноническом порядке — из индексов книг."""
    order, seen = [], set()
    for kn in KNIGI:
        text = (ROOT / kn / "index.html").read_text(encoding="utf-8")
        for slug in CHAP_RX.findall(text):
            if slug not in seen:
                seen.add(slug)
                order.append(slug)
    missing = set(Z.chapter_dirs()) - seen
    if missing:
        raise SystemExit(f"Главы есть на диске, но не перечислены в книгах: "
                         f"{sorted(missing)}")
    return order


def article_list() -> list[str]:
    out = []
    for slug in chapter_order():
        for fp in sorted(glob.glob(str(ROOT / slug / "[0-9][0-9][0-9].html"))):
            out.append(f"{slug}/{Path(fp).name}")
    return out


def check_info(text: str) -> int:
    """Проверить ссылки виджета недельной главы. Возвращает число битых."""
    info = json.loads(INFO_RX.search(text).group(1))
    urls = []
    for key, rec in info.items():
        for u in ([rec["url"]] if rec.get("url") else []) + \
                 [p["url"] for p in rec.get("parts", [])]:
            urls.append((key, u))
    bad = [(k, u) for k, u in urls if not (ROOT / u).exists()]
    for k, u in bad:
        print(f"  БИТАЯ ссылка INFO[{k}] → {u}")
    print(f"INFO: {len(urls)} ссылок, битых {len(bad)}")
    return len(bad)


def main() -> int:
    check_only = "--check" in sys.argv
    index = ROOT / "index.html"
    text = index.read_text(encoding="utf-8")

    arts = article_list()
    body = ", ".join(f'"{a}"' for a in arts)
    new_text = ARTICLES_RX.sub(lambda m: m.group(1) + body + m.group(3), text,
                               count=1)

    old = re.findall(r'"([^"]+)"', ARTICLES_RX.search(text).group(2))
    added, removed = sorted(set(arts) - set(old)), sorted(set(old) - set(arts))
    print(f"ARTICLES: {len(arts)} статей "
          f"(+{len(added)} / -{len(removed)}, порядок из kniga-*/index.html)")
    for a in added[:5]:
        print(f"  + {a}")
    for a in removed[:5]:
        print(f"  - {a}")
    if len(added) > 5 or len(removed) > 5:
        print("  …")

    bad = check_info(text)

    if check_only:
        print("--check: файл не изменён.")
        return 1 if (bad or new_text != text) else 0
    if new_text == text:
        print("index.html: изменений нет.")
    else:
        index.write_text(new_text, encoding="utf-8")
        print("index.html: ARTICLES обновлён.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
