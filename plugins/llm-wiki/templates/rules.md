# LLM Wiki Rules

- すべての知識はページとして蓄積する
- 既存ページがあれば新規作成せず統合する
- 概念は concepts/、設計判断は notes/、画面・人・プロジェクトは pages/ に置く
- 必ず [[ページ名]] でリンクを貼る（相対パス不可・スラッシュ不可）
- 出典（プロジェクト名、ファイルパス、URL等）を frontmatter の `source` と本文に書く
- inbox のファイルは処理後に sources/ へ移動し inbox/ から削除する
  - **移動後に inbox/ が空であることを必ず確認する**（宣言だけで済ませない）
  - **0byte・中身なしのファイルは移動せず削除する**。inbox には中身のあるファイルだけ置く
  - 冪等性のため、取込完了は frontmatter の `type: source` マーカーで示す（全処理の最後にだけ立てる）
- 有用な回答は qa/ に保存する（**任意**。再利用価値の高いQ&Aが出たときのみ）
- ページには YAML frontmatter を付ける（type, genre, summary, tags, related, source, created, updated）
- 変更を加えたら以下を実行して健全性を確認する:
  - `python meta/lint.py`   … 赤リンク・孤立・空・frontmatter・inbox を検査（exit 0 で健全）
  - `python meta/index.py`  … frontmatter から index.md を再生成（手書きしない）
