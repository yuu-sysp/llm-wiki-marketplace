---
name: ingest
description: inbox/ の未処理ソースを Wiki ページへ取り込む。pptx/xlsx/docx/pdf/txt などは md へ自動変換してから、Phase A(収集) → Phase B(編集) の2段で処理する。完了マーカー type:source を最後にだけ立てる冪等設計。「inbox を処理」「wiki ingest」で起動。
---

# LLM Wiki: ingest（inbox 取り込み）

規約 `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/conventions.md` と
判断基準 `.../decision-rules.md` を先に読むこと。

## Phase 0（非 md の変換）

以降の手順は `inbox/*.md` しか見ないため、**最初に必ず変換を走らせる**。

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/convert_inbox.py"
```

pptx / xlsx / docx / pdf / txt / csv / html を md 化し、原本は `sources/_attachments/` へ退避する。
スキップされたものが出た場合の扱い:

- **PDF が「pypdf が未導入」でスキップされた** → ライブラリを入れずに済ませてよい。
  Read ツールで PDF を直接読み、`inbox/<名前>.md` として自分で書き出してから Phase A に進む
  （原本は `sources/_attachments/` へ手で移す）。
- **docx / xlsx / pptx がライブラリ未導入でスキップされた** → Read ツールでは読めない。
  表示された `pip install ...` をユーザーに案内し、そのファイルは今回の対象から外す。
- **`.doc` / `.xls` / `.ppt`（旧バイナリ）** → 変換不可。`.docx` 等で保存し直すようユーザーに依頼する。

## Phase A（収集・分類）

1. `inbox/*.md` を一覧。**0byte・中身なしスタブは処理せず削除**する。
2. 各ファイルを読み、trigger 種別ごとにキーポイントを抽出。
3. ソース原文を `sources/<genre>/` へ移動（frontmatter にメタ付与、**本文は無加工**）。

## Phase B（編集・ページ化）

4. `concepts/ notes/ pages/` の既存ページを検索し、該当があれば統合更新、無ければテンプレートから新規作成。
5. ページ間に `[[リンク]]` を貼る。frontmatter（type/genre/summary/related/created/updated）を埋める。
6. すべて完了した**最後にだけ** ソースの frontmatter に `type: source` を立てる（途中失敗時は未完のまま安全に再実行できる）。

## 仕上げ（必須）

7. `meta/log.md` に追記。
8. 検証:
   ```
   python "${CLAUDE_PLUGIN_ROOT}/scripts/index.py"   # index 再生成
   python "${CLAUDE_PLUGIN_ROOT}/scripts/lint.py"    # 健全性（inbox が空か含む）
   ```
   inbox が空・lint が exit 0 になるまでクローズしない。
   lint の「inbox 未変換ファイル」は Phase 0 の対象漏れ。残っていたら上の扱いに従う。
