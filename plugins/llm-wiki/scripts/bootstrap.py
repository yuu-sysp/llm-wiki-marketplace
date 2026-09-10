#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LLM-Wiki vault の足場を冪等生成し、蓄積方針をセッションに注入する.

- フォルダ構成（concepts/ notes/ pages/ qa/ inbox/ sources/ meta/ _proposals/）を作る。
- meta 配下の雛形（index.md / log.md / rules.md / lint-ignore.txt / template-*.md）を
  「存在しない場合のみ」テンプレートから配置する（既存は決して上書きしない＝冪等）。
- SessionStart フックとして走ったとき、**解決済み vault パスと蓄積方針**を stdout に出す。
  SessionStart の stdout はセッション context に入るため、これが「いつ・何を・どこへ書くか」の
  指示になる。ここで出さないと Stop フック（save_learnings.py）が作る当日スタブを
  誰も埋めず、「自動蓄積」が空回りする。個人の ~/.claude/CLAUDE.md に方針を書く運用は
  特定PC依存になるため、プラグイン側から配る。

インストーラからも SessionStart フックからも同じこのスクリプトを呼ぶ（二重実装回避）。
インストーラ実行時は方針出力が不要なので `--quiet-policy` で抑止する。
vault ルートは argv[1] → 環境変数の順で解決。
  例: python bootstrap.py "D:/資料/LLM-Wiki"
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _vault import print_unresolved_hint, resolve_vault  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
TODAY = datetime.now().strftime("%Y-%m-%d")

DIRS = ["concepts", "notes", "pages", "qa", "inbox", "sources",
        "sources/_attachments",                 # convert_inbox.py が退避する原本置き場
        "meta", "_proposals"]

# (テンプレファイル名, vault内の配置先相対パス)
SEEDS = [
    ("meta-index.md", "meta/index.md"),
    ("meta-log.md", "meta/log.md"),
    ("rules.md", "meta/rules.md"),
    ("lint-ignore.txt", "meta/lint-ignore.txt"),
    ("template-concept.md", "meta/template-concept.md"),
    ("template-page.md", "meta/template-page.md"),
    ("template-qa.md", "meta/template-qa.md"),
]


def render(text: str) -> str:
    return text.replace("{{DATE}}", TODAY)


# SessionStart で毎回 context に載るため、行数は最小限に保つ（増やすときは費用対効果を考える）
POLICY = """\
== LLM Wiki 蓄積方針（llm-wiki プラグイン / SessionStart 注入）==
vault: {vault}
知見が出たら**セッション中にその場で** `{vault}/inbox/{date}-<プロジェクト名>.md` へ追記する。
当日ファイルは Stop フックが用意するので新規作成は不要（既存に追記するだけ）。
記録トリガー → 配置先:
  ライブラリ/クラス/API の使い方を調べた・エラー原因を特定した・同じパターンを2回以上書いた → concepts/
  設計判断をした（なぜAでなくBか。選択肢・理由・トレードオフ）→ notes/
  画面・機能を実装した（画面ID・機能概要・構成）→ pages/
書き方: 見出しに種別を明記（`### [concept] 名前`）／「調べた」ではなく調べた結果そのものを書く／
  コード例を含める／既存ページは `[[ページ名]]` でリンク／クラス名・ライブラリ名は backtick（赤リンク防止）／
  **パスワード・接続文字列・IP 等の資格情報は伏せ字化して書く**。
skill: /llm-wiki:save 保存 · ingest 取込 · query 検索 · lint 検査＋index再生成 · init 初期化
=="""


def print_policy(vault: Path) -> None:
    # 区切り文字を混在させない（`D:\x/inbox/` のような表示を避ける）
    print(POLICY.format(vault=vault.as_posix(), date=TODAY))


def main() -> int:
    argv = [a for a in sys.argv[1:] if a != "--quiet-policy"]
    quiet_policy = "--quiet-policy" in sys.argv
    # resolve_vault は sys.argv を直接見るため、フラグを除いた状態に整えてから呼ぶ
    sys.argv = [sys.argv[0]] + argv

    vault = resolve_vault()
    if vault is None:
        print_unresolved_hint("bootstrap.py")
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

    # 足場の増減があったときだけ報告する（無変化のときは黙る）
    if created:
        print(f"LLM-Wiki bootstrap  (vault: {vault})")
        print(f"  作成: {len(created)}  /  既存スキップ: {len(skipped)}")
        for c in created:
            print("    + " + c)

    # 蓄積方針は毎回出す（これが無いと当日スタブが埋まらない）
    if not quiet_policy:
        print_policy(vault)
    return 0


if __name__ == "__main__":
    sys.exit(main())
