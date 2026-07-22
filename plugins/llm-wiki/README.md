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
| script | `scripts/save_learnings.py` | Stop フック本体 |
| script | `scripts/_vault.py` | vault ルート解決（引数→環境変数） |
| template | `templates/` | ページ・meta の雛形 |

## vault ルートの解決

`vault_root`（plugin.json の userConfig）→ 環境変数 `CLAUDE_PLUGIN_OPTION_VAULT_ROOT` として
スクリプトに渡る。スタンドアロン実行時は引数、または `LLM_WIKI_VAULT_ROOT` でも可。

## スクリプト単体実行

```
python scripts/bootstrap.py "D:/資料/LLM-Wiki"
python scripts/lint.py       "D:/資料/LLM-Wiki"
python scripts/index.py      "D:/資料/LLM-Wiki"
```

## 設計メモ

- **提案ワークフロー** `_proposals/`（pending→applied/rejected）と **curiosity** は設計として想定済み。
  v0.1 では skill 化していない（将来拡張）。
- 既存 vault の frontmatter 一括移行は本プラグインの範囲外（空 vault の新規配布が対象）。
