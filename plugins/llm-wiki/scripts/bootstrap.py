#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM-Wiki vault の足場を冪等生成する.

- フォルダ構成（concepts/ notes/ pages/ qa/ inbox/ sources/ meta/ _proposals/）を作る。
- meta 配下の雛形（index.md / log.md / rules.md / lint-ignore.txt / template-*.md）を
  「存在しない場合のみ」テンプレートから配置する（既存は決して上書きしない＝冪等）。

インストーラからも SessionStart フックからも同じこのスクリプトを呼ぶ（二重実装回避）。
vault ルートは argv[1] → 環境変数の順で解決。
  例: python bootstrap.py "D:/資料/LLM-Wiki"
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import resolve_vault  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
TODAY = datetime.now().strftime("%Y-%m-%d")

DIRS = ["concepts", "notes", "pages", "qa", "inbox", "sources", "meta", "_proposals"]

# (テンプレファイル名, vault内の配置先相対パス)
SEEDS = [
    ("meta-index.md", "meta/index.md"),
    ("meta-log.md", "meta/log.md"),
    ("rules.md", "meta/rules.md"),
    ("lint-ignore.txt", "meta/lint-ignore.txt"),
    ("template-concept.md", "meta/template-concept.md"),
    ("template-page.md", "meta/template-page.md"),
]


def render(text: str) -> str:
    return text.replace("{{DATE}}", TODAY)


def main() -> int:
    vault = resolve_vault()
    if vault is None:
        print("ERROR: vault ルートを指定してください（引数 or LLM_WIKI_VAULT_ROOT）。")
        return 2

    created, skipped = [], []

    for d in DIRS:
        p = vault / d
        if p.is_dir():
            skipped.append(d + "/")
        else:
            p.mkdir(parents=True, exist_ok=True)
            created.append(d + "/")

    for tpl_name, dest_rel in SEEDS:
        dest = vault / dest_rel
        if dest.exists():
            skipped.append(dest_rel)
            continue
        tpl = TEMPLATES / tpl_name
        content = render(tpl.read_text(encoding="utf-8")) if tpl.exists() else ""
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        created.append(dest_rel)

    # SessionStart フックから毎回走るため、新規作成が無いときは静かにする（context汚染回避）
    if created:
        print(f"LLM-Wiki bootstrap  (vault: {vault})")
        print(f"  作成: {len(created)}  /  既存スキップ: {len(skipped)}")
        for c in created:
            print("    + " + c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
