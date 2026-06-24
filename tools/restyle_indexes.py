"""§2.4 enrich_zohar — новый стиль индексов zohar-sulam (справочник, не трекер).

  • Индекс главы:  «Прогресс: N/N · ✅» → «§ 1 – NN»; строки статей ✅ → «§ A – B».
  • Индекс книги:  «Главы: G/G · Статей: A/A» → «Содержит: G глав · A статей»;
                   строки глав «✅ завершено» → «<слаг> · N статей».
  • Корень:        «Прогресс: 52/52 · 1780/1780» → «Содержит: 53 главы · 1780 статей»;
                   строки книг «N/N главы» → «N глав(а/ы)».

bereshit-1/2 уже в новом стиле (их создал split_bereshit). Идемпотентно: главы без
«Прогресс:» пропускаются. Склонения — zsutil.chap_word / stat_word.

Запуск:  python tools/restyle_indexes.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
ROW_HREF_RX = re.compile(r'href="(\d{3})\.html"')
STATUS_RX = re.compile(r'<span class="status[^"]*">.*?</span>(?=</li>)')
BOOK_ROW_RX = re.compile(r'<a href="\.\./([^/]+)/index\.html">(.*?)</a>')


def restyle_chapter(slug: str, data: dict) -> bool:
    fp = ROOT / slug / "index.html"
    text = fp.read_text(encoding="utf-8")
    if "Прогресс:" not in text:
        return False  # уже новый стиль (bereshit-1/2) или иной — пропуск
    ranges = data["ranges"]
    chmin, chmax = data["min"], data["max"]

    # meta: сохранить префикс «Книга: …», заменить «· Прогресс: … Завершена» → «· § 1 – NN»
    rng = f"§ {chmin} {Z.EN} {chmax}" if chmin != 1 else f"§ 1 {Z.EN} {chmax}"
    text = re.sub(r"· Прогресс:[^<]*</p>", f"· {rng}</p>", text, count=1)

    # строки: статус-span → §-диапазон статьи
    def fix_row(line: str) -> str:
        m = ROW_HREF_RX.search(line)
        if not m:
            return line
        n = int(m.group(1))
        a, b = ranges[n]
        return STATUS_RX.sub(
            f'<span class="status done">{Z.fmt_range(a, b)}</span>', line, count=1)

    text = "\n".join(fix_row(ln) if ln.startswith("<li>") else ln
                     for ln in text.split("\n"))
    fp.write_text(text, encoding="utf-8")
    return True


def restyle_book(slug: str, art_counts: dict) -> int:
    """Перестроить kniga-*/index.html. Возвращает число глав в книге (для корня)."""
    fp = ROOT / slug / "index.html"
    text = fp.read_text(encoding="utf-8")

    # порядок глав книги из существующих строк
    chapters = []  # (chap_slug, human)
    for ln in text.split("\n"):
        if ln.startswith("<li>"):
            m = BOOK_ROW_RX.search(ln)
            if m:
                chapters.append([m.group(1), m.group(2)])

    # split bereshit → две главы
    new_chapters = []
    for cslug, human in chapters:
        if cslug == "bereshit":
            new_chapters.append(["bereshit-1", "Берешит 1"])
            new_chapters.append(["bereshit-2", "Берешит 2"])
        else:
            new_chapters.append([cslug, human])

    g = len(new_chapters)
    a = sum(art_counts[c] for c, _ in new_chapters)

    rows = []
    for cslug, human in new_chapters:
        n = art_counts[cslug]
        rows.append(
            f'<li><a href="../{cslug}/index.html">{human}</a>'
            f'<span class="status done">{cslug} · {n} {Z.stat_word(n)}</span></li>')

    # meta «Главы: …» → «Содержит: G глав · A статей»
    text = re.sub(
        r'<p class="meta">[^<]*</p>',
        f'<p class="meta">Содержит: {g} {Z.chap_word(g)} · {a} {Z.stat_word(a)}</p>',
        text, count=1)
    # заменить блок <ul class="toc">…</ul>
    text = re.sub(r'<ul class="toc">.*?</ul>',
                  '<ul class="toc">\n' + "\n".join(rows) + "\n</ul>",
                  text, count=1, flags=re.S)
    fp.write_text(text, encoding="utf-8")
    return g


def restyle_root(book_chap_counts: dict) -> None:
    fp = ROOT / "index.html"
    text = fp.read_text(encoding="utf-8")
    total_chapters = sum(book_chap_counts.values())

    # meta-строка ПЕРВОЙ (снимает «52/52 главы», чтобы не задеть её ниже):
    # «Прогресс: 52/52 главы · 1780/1780 статей.» → «Содержит: 53 главы · 1780 статей.»
    text = re.sub(
        r"Прогресс: \d+/\d+ главы · (\d+)/\d+ статей\.",
        lambda m: (f"Содержит: {total_chapters} {Z.chap_word(total_chapters)} · "
                   f"{m.group(1)} {Z.stat_word(int(m.group(1)))}."),
        text, count=1)
    # head-описания: «52 главы» → «53 главы» (description/og/twitter)
    text = text.replace("52 главы", f"{total_chapters} {Z.chap_word(total_chapters)}")

    # строки книг: «N/N главы» → «{count} глав(а/ы)»
    def fix_book_row(line: str) -> str:
        m = re.search(r'href="(kniga-[^/]+)/index\.html"', line)
        if not m:
            return line
        c = book_chap_counts[m.group(1)]
        return re.sub(r'<span class="status[^"]*">[^<]*</span>',
                      f'<span class="status done">{c} {Z.chap_word(c)}</span>',
                      line, count=1)

    text = "\n".join(fix_book_row(ln) if ln.startswith("<li>") else ln
                     for ln in text.split("\n"))
    fp.write_text(text, encoding="utf-8")
    print(f"root: Содержит {total_chapters} {Z.chap_word(total_chapters)}")


def main() -> int:
    slugs = Z.chapter_dirs()
    art_counts = {s: len(Z.article_files(s)) for s in slugs}

    # §-данные глав
    chap_data = {}
    for s in slugs:
        arts = Z.parse_chapter(s)
        chap_data[s] = {
            "ranges": {x["num"]: (x["para_start"], x["para_end"]) for x in arts},
            "min": min(x["para_start"] for x in arts),
            "max": max(x["para_end"] for x in arts),
        }

    n_styled = sum(restyle_chapter(s, chap_data[s]) for s in slugs)
    print(f"Глав-индексов перестилизовано: {n_styled} (bereshit-1/2 уже новые)")

    books = sorted(p.name for p in ROOT.iterdir()
                   if p.is_dir() and p.name.startswith("kniga-"))
    book_chap_counts = {}
    for b in books:
        g = restyle_book(b, art_counts)
        book_chap_counts[b] = g
        print(f"  {b}: {g} глав")

    restyle_root(book_chap_counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
