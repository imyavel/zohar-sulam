"""Общие утилиты трансформ-скриптов zohar-sulam (enrich_zohar).

Парсинг статей (NNN.html), склонение русских числительных, формат §-диапазона.
Используется split_bereshit / restyle_indexes / build_zohar_index.
Источник истины — сам репозиторий HTML (исходный пайплайн не воскрешается).
"""
from __future__ import annotations
import re
import glob
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # корень репо zohar-sulam

PARA_RX = re.compile(r'<p class="para-start"(?:\s+id="p\d+")?>\s*(\d+)\)')
TITLE_RX = re.compile(r'<title>\s*Статья\s+(\d+)\.\s*(.+?)\s*</title>', re.S)
META_HE_RX = re.compile(r'class="he">(.*?)</span>')
META_RANGE_RX = re.compile(r'Сулам §(\d+)[–-](\d+)')
NNN_RX = re.compile(r'^\d{3}$')
EN = "–"  # en-dash, как в существующих метах статей


def decl(n: int, one: str, few: str, many: str) -> str:
    """Склонение по числу: 1→one (кроме 11), 2–4→few (кроме 12–14), иначе→many."""
    n = abs(int(n))
    d, d2 = n % 10, n % 100
    if d == 1 and d2 != 11:
        return one
    if 2 <= d <= 4 and not 12 <= d2 <= 14:
        return few
    return many


def stat_word(n: int) -> str:
    return decl(n, "статья", "статьи", "статей")


def chap_word(n: int) -> str:
    return decl(n, "глава", "главы", "глав")


def fmt_range(a: int, b: int) -> str:
    """§-диапазон статьи для индекса: «§ 53 – 56», одиночный — «§ 53»."""
    return f"§ {a}" if a == b else f"§ {a} {EN} {b}"


def chapter_dirs() -> list[str]:
    out = []
    for p in sorted(ROOT.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("kniga-") or p.name.startswith("."):
            continue
        if p.name in ("pagefind", "__pycache__", "tools"):
            continue
        if glob.glob(str(p / "[0-9][0-9][0-9].html")):
            out.append(p.name)
    return out


def article_files(slug: str) -> list[Path]:
    return [Path(p) for p in sorted(glob.glob(str(ROOT / slug / "[0-9][0-9][0-9].html")))]


def parse_article(fp: Path) -> dict:
    """{num, title, he, para_start, para_end, paras:[...]} из NNN.html."""
    html = fp.read_text(encoding="utf-8", errors="replace")
    head = html.split("<article", 1)[0]
    mt = TITLE_RX.search(head)
    num = int(fp.stem)
    title = mt.group(2).strip() if mt else ""
    mhe = META_HE_RX.search(head)
    he = mhe.group(1) if mhe else ""
    paras = [int(x) for x in PARA_RX.findall(html)]
    a = paras[0] if paras else 0
    b = paras[-1] if paras else 0
    return {"num": num, "title": title, "he": he,
            "para_start": a, "para_end": b, "paras": paras}


def parse_chapter(slug: str) -> list[dict]:
    return [parse_article(fp) for fp in article_files(slug)]
