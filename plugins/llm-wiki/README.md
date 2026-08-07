# llm-wiki プラグイン

Obsidian 上に知識を蓄積するハイブリッド LLM Wiki。現行運用の強み（自動蓄積・決定論 lint・型別フォルダ）に、
構造・安全・可搬性の仕組みを載せた配布版。

## コンポーネント

| 種別 | 実体 | 役割 |
|---|---|---|
| skill | `skills/{init,save,ingest,query,lint}` | ユーザー操作（`/llm-wiki:<name>`） |
| skill参照 | `skills/_shared/references/` | 記述規約・判断基準 |
| hook | `hooks/hooks.json` | SessionStart=bootstrap(足場冪等生成＋**蓄積方針の注入**) / Stop=save_learnings(当日スタブ確保＋空スタブ掃除) |
| script | `scripts/lint.py` | 決定論的 lint（赤リンク/孤立/空/frontmatter/inbox） |
| script | `scripts/index.py` | frontmatter から index.md 自動生成（ドリフト根治） |
| script | `scripts/bootstrap.py` | vault フォルダ構成＋meta雛形の冪等生成／SessionStart で蓄積方針を出力（`--quiet-policy` で抑止） |
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

## 自動蓄積の仕組み（v0.2）

「自動蓄積」は 2 つの部品の組み合わせで成立する。**片方だけでは空回りする。**

| 部品 | 役割 |
|---|---|
| Stop フック `save_learnings.py` | 当日 `inbox/{日付}-{プロジェクト}.md` の**空の足場**を用意（＋過去日の空スタブ掃除） |
| SessionStart フック `bootstrap.py` | 「いつ・何を・どこへ書くか」の**蓄積方針を stdout でセッション context に注入** |

v0.1 では方針が各利用者の `~/.claude/CLAUDE.md` にしか無く、新規インストールでは
**毎日空のスタブが生成されるだけで誰も埋めない**状態だった。v0.2 でプラグイン側から配るようにした。

方針の内容を変えたい場合は `scripts/bootstrap.py` の `POLICY` を編集する。
SessionStart で毎回 context に載るため、**行数は最小限に保つこと**。

利用者側の `~/.claude/CLAUDE.md` に vault パスや方針を書く必要はない（書くと特定PC依存になる）。

## 設計メモ

- **提案ワークフロー** `_proposals/`（pending→applied/rejected）と **curiosity** は設計として想定済み。
  v0.2 では skill 化していない（将来拡張）。
- 既存 vault の frontmatter 一括移行は本プラグインの範囲外（空 vault の新規配布が対象）。
