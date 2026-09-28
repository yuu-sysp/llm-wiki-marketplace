# llm-wiki プラグイン

Obsidian 上に知識を蓄積するハイブリッド LLM Wiki。現行運用の強み（自動蓄積・決定論 lint・型別フォルダ）に、
構造・安全・可搬性の仕組みを載せた配布版。

## コンポーネント

| 種別 | 実体 | 役割 |
|---|---|---|
| skill | `skills/{init,save,ingest,query,lint}` | ユーザー操作（`/llm-wiki:<name>`） |
| skill参照 | `skills/_shared/references/` | 記述規約・判断基準 |
| hook | `hooks/hooks.json` | SessionStart=bootstrap(足場冪等生成＋**蓄積方針の注入**＋当日スタブ確保＋inbox滞留の通知) / Stop=save_learnings(当日スタブ確保＋空スタブ掃除) |
| script | `scripts/lint.py` | 決定論的 lint（赤リンク/孤立/空/frontmatter/inbox）。コード内の `[[ ]]` は対象外・`![[添付]]` は実在確認・ページ名は大文字小文字を区別しない |
| script | `scripts/index.py` | `meta/index.md`（genre別一覧）と `meta/keywords.md`（語→ページ索引）を自動生成 |
| script | `scripts/bootstrap.py` | vault フォルダ構成＋meta雛形の冪等生成／SessionStart で蓄積方針を出力（`--quiet-policy` で抑止） |
| script | `scripts/convert_inbox.py` | inbox の pptx/xlsx/docx/pdf/txt 等を md 化（原本は `sources/_attachments/` へ退避） |
| script | `scripts/save_learnings.py` | Stop フック本体 |
| script | `scripts/_vault.py` | vault ルート解決（引数→環境変数）・inbox のスタブ／未処理判定・当日スタブ生成・frontmatter 分割・コード除去の共通処理 |
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

## 自動蓄積の仕組み

「自動蓄積」は 2 つの部品の組み合わせで成立する。**片方だけでは空回りする。**

| 部品 | 役割 |
|---|---|
| Stop フック `save_learnings.py` | 当日 `inbox/{日付}-{プロジェクト}.md` の**空の足場**を用意（＋過去日の空スタブ掃除） |
| SessionStart フック `bootstrap.py` | 「いつ・何を・どこへ書くか」の**蓄積方針を stdout でセッション context に注入**。同じ当日足場もここで用意し、方針には実ファイル名を出す（Stop だけだと最初の応答が終わるまで追記先が無い） |

v0.1 では方針が各利用者の `~/.claude/CLAUDE.md` にしか無く、新規インストールでは
**毎日空のスタブが生成されるだけで誰も埋めない**状態だった。v0.2 でプラグイン側から配るようにした。

方針の内容を変えたい場合は `scripts/bootstrap.py` の `POLICY` を編集する。
SessionStart で毎回 context に載るため、**行数は最小限に保つこと**。

利用者側の `~/.claude/CLAUDE.md` に vault パスや方針を書く必要はない（書くと特定PC依存になる）。

## 検索索引（`meta/keywords.md`）

`index.md` に載るのはページ名と summary だけなので、略語・テーブル名・エラーコードからは辿れない。
`keywords.md` は **語 → ページ** の逆引き索引で、query の grep フォールバックを減らす。

材料は2つ:

- **frontmatter の `tags`** … 人が明示した語。索引の主体なので、ページ名に出ない語
  （略語・別名・テーブル名・ライブラリ名）を入れる。
- **本文見出しのうち識別子らしいもの** … `TENMST` `runtimeconfig.json` `ProcessTmjbfil` など。
  「英数字で始まり日本語2文字以下」で判定する。`確認方法` `関連` のような節ラベルは日本語主体
  なので自動的に外れる。手書きの除外リストは腐るので持たない。

出現ページ数での足切りはしない。よく使うテーブル名ほど多くのページに出るため、頻度で落とすと
最も検索される語から消える（節ラベル対策は識別子判定が担う）。1語あたりのページ数だけ
`KEYWORD_MAX_PAGES`（既定4）で打ち切る。`wpf`（実測56ページ）のような大分類は全件並べても
絞り込めないので件数だけ示す。

> サイズの目安: 186ページ・360タグの vault で約 36KB（`index.md` は約 20KB）。
> ページ数にほぼ比例するので、数百ページ規模になったら `KEYWORD_MAX_PAGES` を下げるか
> genre 別に分割する。

## inbox 滞留の通知

自動蓄積は「溜める」側だけが自動で、片付け（ingest）は人が思い出したときだけ。放っておくと
数十日分が積む。SessionStart は毎回 context に載る唯一の場所なので、そこに1行だけ出す。

```
inbox: 未処理 14件（最古 39日前: 2026-08-07-MGMESTEST.md）→ /llm-wiki:ingest を検討
```

- 「未処理」= 中身のある `.md` ／ 非 md（未変換）／ フォルダ。**中身なしスタブは数えない**
  （Stop フックが毎日作るものなので、それで催促すると毎日鳴る）
- 閾値は `BACKLOG_MIN_COUNT`（既定3件）か `BACKLOG_MIN_DAYS`（既定7日）のどちらか超過時のみ
- インストーラ経路（`--quiet-policy`）では出さない

## 設計メモ

- **提案ワークフロー** `_proposals/`（pending→applied/rejected）と **curiosity** は設計として想定済み。
  現時点では skill 化していない（将来拡張）。
- 既存 vault の frontmatter 一括移行は本プラグインの範囲外（空 vault の新規配布が対象）。
- vault の `meta/template-*.md` は `{{DATE}}` を置換せずに配置する（ページ作成時に置き換える）。
  v0.4.0 以前に初期化した vault は雛形の日付が初期化日で固定されているので、
  `meta/template-*.md` を削除して `/llm-wiki:init` を実行すると作り直せる。
- `index.py` は中身が前回と同じ（「最終更新」日付だけ違う）なら書き込まない。
