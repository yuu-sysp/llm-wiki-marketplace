# llm-wiki プラグイン

Obsidian 上に知識を蓄積するハイブリッド LLM Wiki。現行運用の強み（自動蓄積・決定論 lint・型別フォルダ）に、
構造・安全・可搬性の仕組みを載せた配布版。

## コンポーネント

| 種別 | 実体 | 役割 |
|---|---|---|
| skill | `skills/{init,save,ingest,query,lint}` | ユーザー操作（`/llm-wiki:<name>`） |
| skill参照 | `skills/_shared/references/` | 記述規約・判断基準 |
| hook | `hooks/hooks.json` | SessionStart=bootstrap(足場冪等生成) / Stop=save_learnings(自動蓄積＋空スタブ掃除) |
| script | `scripts/lint.py` | 決定論的 lint（赤リンク/孤立/空/frontmatter/inbox） |
| script | `scripts/index.py` | frontmatter から index.md 自動生成（ドリフト根治） |
| script | `scripts/bootstrap.py` | vault フォルダ構成＋meta雛形の冪等生成 |
| script | `scripts/convert_inbox.py` | inbox の pptx/xlsx/docx/pdf/txt 等を md 化（原本は `sources/_attachments/` へ退避） |
| script | `scripts/save_learnings.py` | Stop フック本体 |
| script | `scripts/_vault.py` | vault ルート解決（引数→環境変数） |
| template | `templates/` | ページ・meta の雛形 |

## 依存

lint / index / bootstrap / save_learnings は**標準ライブラリのみ**で動く（CI・cron で回せる）。
`convert_inbox.py` だけ、Office/PDF を扱うときに次を使う（未導入なら該当ファイルをスキップして続行）。

```
pip install python-docx openpyxl python-pptx pypdf
```

txt / csv / tsv / html / json は追加ライブラリ無しで変換できる。
PDF は pypdf が無くても、ingest 時に Claude の Read ツールが直接読める。

## vault ルートの解決

`vault_root`（plugin.json の userConfig）→ 環境変数 `CLAUDE_PLUGIN_OPTION_VAULT_ROOT` として
スクリプトに渡る。スタンドアロン実行時は引数、または `LLM_WIKI_VAULT_ROOT` でも可。

## スクリプト単体実行

```
python scripts/bootstrap.py     "D:/資料/LLM-Wiki"
python scripts/convert_inbox.py "D:/資料/LLM-Wiki"
python scripts/lint.py          "D:/資料/LLM-Wiki"
python scripts/index.py         "D:/資料/LLM-Wiki"
```

## 設計メモ

- **提案ワークフロー** `_proposals/`（pending→applied/rejected）と **curiosity** は設計として想定済み。
  v0.1 では skill 化していない（将来拡張）。
- 既存 vault の frontmatter 一括移行は本プラグインの範囲外（空 vault の新規配布が対象）。
