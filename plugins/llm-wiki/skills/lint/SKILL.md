---
name: lint
description: LLM Wiki の健全性を検査し index を再生成する。赤リンク・孤立ページ・空ファイル・frontmatter欠落・inbox残存を機械検出し、meta/index.md を frontmatter から再生成する。「wiki lint」「wiki を lint」で起動。
---

# LLM Wiki: lint（健全性検査＋index再生成）

## 手順

1. 機械検査を実行:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py"
   ```
   - exit 0 = 健全。1件以上あれば各項目（赤リンク/孤立/空/frontmatter/inbox）を提示する。
2. index を frontmatter から再生成:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/index.py"
   ```
3. 検出項目のうち **機械的に直せるもの**（赤リンクの [[]] 誤用→backtick化、arphan→リンク追加）は
   直接修正してよい。**判断が要るもの**（矛盾・missing-page 新規作成の是非）は
   `_proposals/` に提案として残すか、ユーザーに確認する。
4. 意図的に残す赤リンク（将来ページ化予定）は `meta/lint-ignore.txt` に1行追加する。

規約・判断基準は `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/` を参照。
