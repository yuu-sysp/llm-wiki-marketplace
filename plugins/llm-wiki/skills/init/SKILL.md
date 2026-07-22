---
name: init
description: LLM Wiki の vault を初期化する。フォルダ構成（concepts/notes/pages/inbox/sources/meta/_proposals）と meta 雛形（index/log/rules/lint-ignore/templates）を冪等生成する。「wiki init」「wiki を初期化」で起動。
---

# LLM Wiki: init（vault 初期化）

vault ルートは環境変数 `CLAUDE_PLUGIN_OPTION_VAULT_ROOT` から解決される（インストール時に設定済み）。

## 手順

1. 次を実行して足場を生成する（既存は上書きしない＝何度実行しても安全）:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/bootstrap.py"
   ```
2. 生成結果（作成/スキップ）をユーザーに報告する。
3. 続けて `python "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py"` を実行し、初期状態が健全（exit 0）であることを確認する。

規約は `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/conventions.md` を参照。
