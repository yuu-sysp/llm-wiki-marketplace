# LLM Wiki 記述規約

すべての skill 操作はこの規約に従う。vault ルートは環境変数
`CLAUDE_PLUGIN_OPTION_VAULT_ROOT`（プラグイン userConfig `vault_root` 由来）で解決する。
シェルからは `python "${CLAUDE_PLUGIN_ROOT}/scripts/xxx.py"` で各スクリプトを呼ぶ
（vault は環境変数から自動解決される）。

## フォルダ構成

| フォルダ | 用途 |
|---|---|
| `concepts/` | 概念・技術パターン・ライブラリの知見 |
| `notes/`    | 設計判断メモ（なぜAでなくBか。Why とトレードオフを書く） |
| `pages/`    | 画面・人・プロジェクト・組織 |
| `qa/`       | Q&Aアーカイブ（任意。再利用価値が高いときのみ） |
| `inbox/`    | 未処理ソースの投入口（処理後 sources/ へ移動、または削除） |
| `sources/`  | 取り込み済みの生ソース（原文保持・改変禁止） |
| `meta/`     | index.md / log.md / rules.md / lint-ignore.txt / テンプレート |
| `_proposals/` | lint/curiosity の修正提案（pending → applied/rejected） |

## frontmatter スキーマ（全ページ必須）

```yaml
---
type: concept | note | page | synthesis | source | index
genre: <ジャンル slug>          # index.py のグルーピングキー
summary: "12〜30字の1行要約"     # index.py がそのまま index.md に出す
tags: []
related: ["[[関連ページ]]"]
source: "プロジェクト名/ファイル or URL"
created: YYYY-MM-DD
updated: YYYY-MM-DD              # 更新時のみ変える。created は不変
---
```

lint の最小必須は `type:` と `created:`。index を綺麗に出すには `genre` と `summary` も入れる。

## リンク（Obsidian wikilink）

- ページ参照: `[[ページ名]]`（相対パス不可・スラッシュ不可）
- 別名: `[[ページ名|表示]]` / セクション: `[[ページ名#見出し]]`
- クラス名・ライブラリ名など「ページにしないもの」は `[[ ]]` で囲まず `` `backtick` `` にする（赤リンク量産を防ぐ）

## 日付

- 実時刻を使う（`date +%Y-%m-%d`）。新規は `created = updated = 今日`、更新時は `updated` のみ。

## 禁止事項

- frontmatter なしページ／相対パス wikilink／`sources/` 内の本文改変（frontmatter メタのみ可）
- index.md の手書き（必ず `python meta/index.py` で再生成）
