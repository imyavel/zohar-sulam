"""§2.1 enrich_zohar — якоря параграфов id="pNN".

Каждому `<p class="para-start">NN)` добавляет `id="pNN"` → URL `…/NNN.html#pNN`.
Идемпотентно (уже есть id → пропуск). Меняет ТОЛЬКО атрибут id, текст/разметка
тела неизменны. Прогон по всем главам (после split — bereshit-1/2, без bereshit).
При будущем пополнении корпуса — повторный прогон (безопасен).

Запуск:  python tools/add_para_anchors.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zsutil as Z  # noqa: E402

# только не-заякоренные: после '"para-start"' идёт сразу '>'
RX = re.compile(r'<p class="para-start">(\s*)(\d+)\)')


def main() -> int:
    files = 0
    added = 0
    for slug in Z.chapter_dirs():
        for fp in Z.article_files(slug):
            text = fp.read_text(encoding="utf-8")
            n = [0]

            def repl(m: re.Match) -> str:
                n[0] += 1
                return f'<p class="para-start" id="p{m.group(2)}">{m.group(1)}{m.group(2)})'

            new = RX.sub(repl, text)
            if new != text:
                fp.write_text(new, encoding="utf-8")
                files += 1
                added += n[0]
    print(f"Заякорено: {added} параграфов в {files} файлах.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
