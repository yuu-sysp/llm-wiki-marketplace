#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meta/index.md を各ページの frontmatter から自動生成する.

現行の「手書き index」のドリフト（赤リンク・記載漏れ）を根治するための生成器。
各ページの frontmatter から genre / summary を読み、genre 別にグルーピングして
`- [[ページ名]] — summary` の一覧を書き出す。手書きの1行説明は summary に一元化する。

vault ルートは argv[1] → 環境変数の順で解決。
  例: python index.py "D:/資料/LLM-Wiki"
"""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import resolve_vault  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TODAY = datetime.now().strftime("%Y-%m-%d")
CONTENT_DIRS = ["concepts", "pages", "notes", "qa"]


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="cp932", errors="replace")


def parse_frontmatter(text: str) -> dict:
    """先頭 --- ... --- の簡易 key: value パース（外部YAML非依存）。"""
    if not text.lstrip().startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out = {}
    for ln in parts[1].splitlines():
        m = re.match(r"\s*([A-Za-z_]+)\s*:\s*(.*)$", ln)
        if m:
            val = m.group(2).strip().strip('"').strip("'")
            out[m.group(1)] = val
    return out


def main() -> int:
    vault = resolve_vault()
    if vault is None:
        print("ERROR: vault ルートを指定してください。")
        return 2
    if not vault.is_dir():
        print(f"ERROR: vault が存在しません: {vault}")
        return 2

    # genre -> [(page_name, summary)]
    groups = {}
    total = 0
    for d in CONTENT_DIRS:
        base = vault / d
        if not base.is_dir():
            continue
        for p in sorted(base.glob("*.md")):
            fm = parse_frontmatter(read(p))
            genre = fm.get("genre") or "未分類"
            summary = fm.get("summary") or ""
            groups.setdefault(genre, []).append((p.stem, summary))
            total += 1

    lines = [
        "# Wiki Index",
        "",
        f"最終更新: {TODAY}",
        "",
        "> このファイルは `python meta/index.py` で自動生成されます。**手で編集しないでください。**",
        "> 1行説明は各ページ frontmatter の `summary:` を編集してください。",
        "",
    ]
    for genre in sorted(groups):
        lines.append(f"## {genre}")
        lines.append("")
        for name, summary in sorted(groups[genre]):
            lines.append(f"- [[{name}]]" + (f" — {summary}" if summary else ""))
        lines.append("")

    out = vault / "meta" / "index.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"index.md を再生成しました: {out}  （{total} ページ / {len(groups)} genre）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
