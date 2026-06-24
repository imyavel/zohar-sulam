"""§2.0 enrich_zohar — разделить главу `bereshit` на две обычные главы.

  bereshit/001..049 → bereshit-1/001..049  (номера те же; «Берешит 1»)
  bereshit/050..102 → bereshit-2/001..053  (новый = старый−49; «Берешит 2»)

Тело перевода (между <article…> и </article>) НЕ трогается (якоря id добавит
отдельный проход add_para_anchors.py). Меняются только head-метаданные
(title/h1/крошки/canonical/og/JSON-LD/meta) и навигация. Генерирует индексы
bereshit-1/index.html и bereshit-2/index.html сразу в НОВОМ стиле (§2.4-C).
Старый каталог bereshit/ удаляется целиком. Идемпотентно (если bereshit/ нет — выход).

Запуск:  python tools/split_bereshit.py   (из корня репо zohar-sulam)
"""
from __future__ import annotations
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

ROOT = Z.ROOT
KNIGA_HUMAN = "Берешит (Бытие)"
NAV_RX = re.compile(r'<nav class="article-nav">.*?</nav>', re.S)


def make_nav(new_n: int, last: int) -> str:
    prev = (f'<span><a href="{new_n-1:03d}.html">← Статья {new_n-1}</a></span>'
            if new_n > 1 else "<span>&nbsp;</span>")
    nxt = (f'<span><a href="{new_n+1:03d}.html">Статья {new_n+1} →</a></span>'
           if new_n < last else "<span>&nbsp;</span>")
    return (f'<nav class="article-nav">{prev}'
            f'<a href="index.html">Оглавление главы</a>{nxt}</nav>')


def rewrite_article(src: Path, slug: str, human: str,
                    old_n: int, new_n: int, last: int) -> str:
    """Вернуть новое содержимое статьи (head адаптирован, nav пересобран, тело as-is)."""
    text = src.read_text(encoding="utf-8")
    head, sep, tail = text.partition("<article")

    # --- head: имя главы во всех местах (крошка-текст, meta-строка, JSON-LD name) ---
    head = head.replace("Берешит (В начале)", human)
    # слаг в URL (canonical, og:url, JSON-LD items) — якорим на 'zohar-sulam/bereshit/'
    head = head.replace("zohar-sulam/bereshit/", f"zohar-sulam/{slug}/")
    # номер статьи (только часть 2): title/og/tw/h1 («Статья N.»), JSON-LD name, крошка, URL
    if new_n != old_n:
        head = re.sub(rf"Статья {old_n}\.", f"Статья {new_n}.", head)
        head = head.replace(f'"name":"Статья {old_n}"',
                            f'"name":"Статья {new_n}"')
        head = re.sub(rf"(›</span>)Статья {old_n}(</div>)",
                      rf"\g<1>Статья {new_n}\g<2>", head)
        head = head.replace(f"{slug}/{old_n:03d}.html",
                            f"{slug}/{new_n:03d}.html")

    # --- tail: пересобрать навигацию (тело статьи неизменно) ---
    tail = NAV_RX.sub(make_nav(new_n, last), tail, count=1)
    return head + sep + tail


def build_index(slug: str, human: str, old_index_text: str,
                arts: list[dict], maxpara: int) -> str:
    """Индекс главы в НОВОМ стиле (§2.4-C), head/footer — из старого bereshit/index.html."""
    head, sep, rest = old_index_text.partition("<h1>")
    foot = rest[rest.index("<footer"):]
    n_arts = len(arts)

    head = head.replace("Берешит (В начале)", human)
    head = head.replace("zohar-sulam/bereshit/", f"zohar-sulam/{slug}/")
    head = re.sub(r"— 102 статьи\.",
                  f"— {n_arts} {Z.stat_word(n_arts)}.", head)

    rows = []
    for a in arts:
        n = a["num"]
        rows.append(
            f'<li><span class="num">{n}.</span>'
            f'<a href="{n:03d}.html">Статья {n}. {a["title"]}</a>'
            f'<span lang="he" dir="rtl" class="he">{a["he"]}</span>'
            f'<span class="status done">{Z.fmt_range(a["para_start"], a["para_end"])}</span></li>'
        )
    body = (f'<h1>{human}</h1>\n'
            f'<p class="meta">Книга: {KNIGA_HUMAN} · § 1 {Z.EN} {maxpara}</p>\n'
            f'<ul class="toc">\n' + "\n".join(rows) + "\n</ul>\n\n")
    return head + body + foot


def main() -> int:
    old_dir = ROOT / "bereshit"
    if not old_dir.exists():
        print("bereshit/ не найден — split уже выполнен, пропуск.")
        return 0

    old_index_text = (old_dir / "index.html").read_text(encoding="utf-8")

    plan = []  # (src_path, slug, human, old_n, new_n, last)
    for fp in Z.article_files("bereshit"):
        old_n = int(fp.stem)
        if old_n <= 49:
            plan.append((fp, "bereshit-1", "Берешит 1", old_n, old_n, 49))
        else:
            plan.append((fp, "bereshit-2", "Берешит 2", old_n, old_n - 49, 53))

    for slug in ("bereshit-1", "bereshit-2"):
        (ROOT / slug).mkdir(exist_ok=True)

    for src, slug, human, old_n, new_n, last in plan:
        content = rewrite_article(src, slug, human, old_n, new_n, last)
        dst = ROOT / slug / f"{new_n:03d}.html"
        dst.write_text(content, encoding="utf-8")
    print(f"Перенесено статей: {len(plan)} "
          f"(bereshit-1: 49, bereshit-2: 53)")

    # индексы из НОВЫХ файлов
    for slug, human in (("bereshit-1", "Берешит 1"), ("bereshit-2", "Берешит 2")):
        arts = Z.parse_chapter(slug)
        maxpara = max(a["para_end"] for a in arts)
        idx = build_index(slug, human, old_index_text, arts, maxpara)
        (ROOT / slug / "index.html").write_text(idx, encoding="utf-8")
        print(f"  {slug}/index.html: {len(arts)} статей, § 1 {Z.EN} {maxpara}")

    shutil.rmtree(old_dir)
    print("Старый каталог bereshit/ удалён.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
