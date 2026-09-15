---
name: lint
description: LLM Wiki の健全性を検査し索引を再生成する。赤リンク・孤立ページ・空ファイル・frontmatter欠落・inbox残存を機械検出し、meta/index.md と meta/keywords.md を再生成する。「wiki lint」「wiki を lint」で起動。
---

# LLM Wiki: lint（健全性検査＋index再生成）

## 手順

1. 機械検査を実行:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py"
   ```
   - exit 0 = 健全。1件以上あれば各項目（赤リンク/孤立/空/frontmatter/inbox）を提示する。
2. 索引を再生成（`meta/index.md` と `meta/keywords.md` の両方が書き換わる）:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/index.py"
   ```
   - `index.md` … genre 別のページ一覧（frontmatter の `summary`）
   - `keywords.md` … 語 → ページの索引（frontmatter の `tags` ＋本文見出しの識別子）
   - どちらも毎回全書き換え。**手で編集しても次回消える。**
3. 検出項目のうち **機械的に直せるもの**（赤リンクの [[]] 誤用→backtick化、孤立ページ→リンク追加）は
   直接修正してよい。**判断が要るもの**（矛盾・missing-page 新規作成の是非）は
   `_proposals/` に提案として残すか、ユーザーに確認する。
4. 意図的に残す赤リンク（将来ページ化予定）は `meta/lint-ignore.txt` に1行追加する。

規約・判断基準は `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/` を参照。
