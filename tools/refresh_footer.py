"""Обновить общий футер на всех страницах сайта.

  * «Последняя сборка» — дата в <p class="build-date"> (по умолчанию сегодня,
    иначе --date YYYY-MM-DD).
  * Счётчик GoatCounter — форматирование числа. API отдаёт уже отформатированную
    строку («1 545», разделитель — NBSP), поэтому Number() без чистки давал NaN
    и футер писал «всего не число просмотров».

Футер во всех страницах байт-в-байт одинаков — правка чисто текстовая.

Запуск:  python tools/refresh_footer.py [--date 2026-08-09] [--check]
Идемпотентно: повторный запуск с той же датой ничего не меняет.
"""
from __future__ import annotations
import glob
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
BUILD_RX = re.compile(r'(<p class="build-date">[^<]*<time datetime=")'
                      r'(\d{4}-\d{2}-\d{2})(">)(\d{4}-\d{2}-\d{2})(</time>)')
FMT_OLD = 'function fmt(n){return Number(n).toLocaleString("ru-RU");}'
# GoatCounter отдаёт "1 545" (NBSP как разделитель тысяч) — чистим перед Number.
FMT_NEW = ('function fmt(n){var v=Number(String(n).replace(/[^0-9]/g,""));'
           'return isFinite(v)?v.toLocaleString("ru-RU"):"—";}')


def main() -> int:
    argv = sys.argv[1:]
    check_only = "--check" in argv
    if "--date" in argv:
        stamp = argv[argv.index("--date") + 1]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
            raise SystemExit(f"--date ждёт YYYY-MM-DD, получено {stamp!r}")
    else:
        stamp = date.today().isoformat()

    pages = [p for p in glob.glob("**/*.html", root_dir=ROOT, recursive=True)
             if not p.startswith("pagefind")]
    dated = fixed = 0
    for rel in pages:
        fp = ROOT / rel
        # newline="" — файлы в репо с CRLF, переводы строк не трогаем
        with open(fp, encoding="utf-8", newline="") as fh:
            text = fh.read()
        new = BUILD_RX.sub(lambda m: m.group(1) + stamp + m.group(3) + stamp
                           + m.group(5), text)
        if new != text:
            dated += 1
        if FMT_OLD in new:
            new = new.replace(FMT_OLD, FMT_NEW)
            fixed += 1
        if new != text and not check_only:
            with open(fp, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)

    print(f"страниц: {len(pages)}")
    print(f"  дата сборки → {stamp}: обновлено {dated}")
    print(f"  fmt() счётчика починен: {fixed}")
    if check_only:
        print("--check: файлы не изменены.")
        return 1 if (dated or fixed) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
