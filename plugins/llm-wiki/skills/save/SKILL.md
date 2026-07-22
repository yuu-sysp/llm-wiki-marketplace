---
name: save
description: 直前の会話・作業で得た知見を Wiki ページ化する。調べたAPI・特定したエラー原因・設計判断などを concepts/notes/pages の適切な場所へ追記または新規作成する。「wiki に保存」「wiki save」で起動。
---

# LLM Wiki: save（会話→ページ化）

規約 `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/conventions.md` と
判断基準 `.../decision-rules.md` に従う。

## 手順

1. 会話から蓄積価値のある知見を抽出（ライブラリ/クラス/APIの使い方、エラー原因と解決、
   2回以上書いたパターン、設計判断、新機能）。**保存基準**を満たさないものは保存しない。
2. 既存ページを検索し「新規作成 / 既存へ追記 / 保存しない」を判断（decision-rules.md）。
3. 決めたフォルダにテンプレートで作成 or 追記。frontmatter を埋め、`[[リンク]]` を貼る。
   - クラス名・ライブラリ名は `[[ ]]` にせず backtick にする。
4. `meta/log.md` に追記。
5. 検証:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/index.py"
   python "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py"
   ```
