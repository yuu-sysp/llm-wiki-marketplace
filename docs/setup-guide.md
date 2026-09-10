# LLM Wiki プラグイン — セットアップ資料

Claude Code で「調べたこと・エラー原因・設計判断」を自動で貯め、Obsidian で読める Wiki に育てる仕組み。
構成: **① ねらい → ② PC導入 → ③ 解説 → ④ 全社展開**。

---

## ① ねらい（なぜ作ったか）

### 解決したい課題
- 調べた知見・ハマりどころが**セッションごとに消える**。同じことを何度も調べ直す。
- 手書きの索引は**すぐ陳腐化**する（リンク切れ・記載漏れ）。
- 知識の仕組みが特定PCに**ハードコード**され、新しいPCへ持ち運べない。

### 設計思想 — 2つの流儀のハイブリッド
| 取り込んだ強み | 由来 |
|---|---|
| 作業中に**自動で**知見を貯める（動詞を叩かなくても溜まる） | 現行運用 |
| **決定論的な lint**（機械的に確実に壊れを検出、CIで使える） | 現行運用 |
| type別フォルダ（concepts/notes/pages）の明快さ | 現行運用 |
| **index を frontmatter から自動生成**（手書きドリフトを根治） | ハイブリッド |
| **冪等な取り込み**（Phase A/B＋`type:source`完了マーカーで壊れない） | Karpathy/TAAT流 |
| **提案ワークフロー**（AIの変更提案を人間が検収）※設計のみ | Karpathy/TAAT流 |
| vault パスの**外部化**（userConfig）で新規PCへ可搬 | ハイブリッド |

### 何が嬉しいか
- Claude Code で普通に開発するだけで、知見が `inbox/` に溜まり、Wiki ページへ整理できる。
- `lint` でいつでも「壊れゼロ」を機械保証。`index` は常に最新。
- プラグイン＋インストーラなので、**新規PCでも数コマンドで同じ環境**が立ち上がる。

---

## ② PC導入（新規PCに入れる）

まず自分のPCで動かす手順。public / private / インストーラの3経路。

### ⚡ 最短手順（新規PC・これだけ読めばよい）

```powershell
git clone https://github.com/yuu-sysp/llm-wiki-marketplace.git
cd llm-wiki-marketplace
.\install.bat
```

1. **保存先をダイアログで選ぶ**（D: など別ドライブも可。選んだフォルダ直下に `LLM-Wiki` が作られる）
2. **Claude Code を完全に終了して起動し直す** ← ★これを飛ばすと必ず失敗する（2.8）
3. `claude plugin list` で `llm-wiki@llm-wiki-marketplace` が `enabled` なら成功。
   Claude Code で `/llm-wiki:lint` が動けば完了

Python が無いPCは `.\install.bat -InstallPython`。
詳細・GUIのみの環境・トラブル時は以下 2.1〜2.9 を参照。

### 2.1 前提
- **Python 3** が PATH にある（scripts が Python）。無い場合はインストーラの `-InstallPython` で自動導入可（2.5）。
- **Claude Code**：CLI か **デスクトップアプリ**のどちらか。プラグイン登録に必要（登録方法は下記）。
- （private リポジトリから入れる場合）GitHub 認証
- inbox で **pptx/xlsx/docx/pdf** を扱うなら変換ライブラリ（`install.bat` が自動導入。オフライン環境は `-NoDocLibs` で省略可 → 3.4）

### 2.2 public リポジトリの場合（最短）
Claude Code（CLI・デスクトップどちらでも）で：
```
/plugin marketplace add yuu-sysp/llm-wiki-marketplace
/plugin install llm-wiki@llm-wiki-marketplace
```
インストール時に **vault 保存先**を尋ねられる。初回セッションの SessionStart フックがフォルダ構成を自動生成。

### 2.3 private リポジトリの場合（Windows）
`owner/repo` 短縮形は既定で SSH クローンになるため、HTTPS を使うなら**フルURL**で指定する。
```powershell
winget install GitHub.cli          # 未導入なら
gh auth login                      # 一度だけ（対話ログイン）
gh auth setup-git                  # git 認証ヘルパー設定
claude plugin marketplace add https://github.com/yuu-sysp/llm-wiki-marketplace.git
claude plugin install llm-wiki@llm-wiki-marketplace --config vault_root="D:\資料\LLM-Wiki"
```
SSH運用なら `git@github.com:yuu-sysp/llm-wiki-marketplace.git` を使う（`gh` 不要）。

### 2.4 インストーラでフォルダ生成まで一括
```powershell
git clone https://github.com/yuu-sysp/llm-wiki-marketplace.git
cd llm-wiki-marketplace
.\install.bat                                  # 保存先はダイアログで選ぶ
.\install.bat -VaultRoot "D:\資料\LLM-Wiki"    # パスを直接指定する場合
```
**`-VaultRoot` を省略すると、エクスプローラー風のフォルダ選択ダイアログが開く**（`install.bat` のダブルクリックでも同じ）。
ツリーのルートは「PC」なので **D: など別ドライブも選べる**し、「新しいフォルダー」でその場に作れる。
選んだフォルダの**直下に `LLM-Wiki` フォルダを作る**（`LLM-Wiki` 自体を選んだ場合は二重にしない）。

| 操作 | 結果 |
|---|---|
| `D:\資料` を選ぶ | vault は `D:\資料\LLM-Wiki` |
| `D:\資料\LLM-Wiki` を選ぶ | vault は `D:\資料\LLM-Wiki`（二重にしない） |
| キャンセル | **中止**（勝手な場所には作らない）。パス指定か `-NoPrompt` で再実行 |
| `-NoPrompt` | ダイアログを出さず既定 `~\Documents\LLM-Wiki`（CI・無人実行用） |

Python 検出 → プラグイン登録（claude CLI があれば）→ vault 生成 → 初期 lint まで実行。
CLI が無ければフォルダ生成まで行い、**デスクトップアプリでの登録手順を表示**する（2.6）。

### 2.5 Python が無い場合の自動インストール
インストーラに `-InstallPython` を付けると、Python が無いとき自動導入する。**PATH 登録も自動**で、
導入直後の同じシェルで使えるよう PATH を再読込するため、ユーザーは環境変数を触らなくてよい。
```powershell
.\install.bat -VaultRoot "D:\資料\LLM-Wiki" -InstallPython
```
- 導入方式: **winget**（`Python.Python.3.12`、ユーザースコープ・管理者権限不要）→ 失敗時 **python.org 公式インストーラ**（`/quiet PrependPath=1`）にフォールバック。
- `python` と `py` の両ランチャーを検出。既に Python 3 があればそれを使う（自動導入しない）。

### 2.6 デスクトップアプリだけの場合（CLI不要でGUI登録）
CLI が無くても、デスクトップアプリの GUI でプラグイン登録できる（アプリは CLI と同じ `~/.claude` を読む）。
1. プロンプト横の **[＋] → Plugins**（または chat に `/plugin` と入力）
2. **Marketplaces タブ → Add marketplace** → URL を貼付:
   `https://github.com/yuu-sysp/llm-wiki-marketplace.git`
3. **Discover タブ** → `llm-wiki` を選び **Install** → スコープ **User** → `vault_root` に保存先を入力 → **Confirm**
4. `/reload-plugins` でリロード（`/llm-wiki:init` 等が `/` メニューに出れば成功）

CLI も入れたい場合（依存なし・自動更新・管理者権限不要）:
```powershell
irm https://claude.ai/install.ps1 | iex
```

### 2.7 vault の保存先（**D ドライブは必須ではない**）
本資料に出てくる `D:\資料\LLM-Wiki` は**単なる例**。仕組み自体はドライブ構成に依存しない。

パス解決の優先順（`scripts/_vault.py`）:
1. スクリプトの第1引数
2. 環境変数 `CLAUDE_PLUGIN_OPTION_VAULT_ROOT`（プラグイン userConfig `vault_root` 由来）
3. 環境変数 `LLM_WIKI_VAULT_ROOT`

`install.ps1` は `-VaultRoot` 未指定ならフォルダ選択ダイアログを出し（2.4）、GUI が使えない環境では **`~\Documents\LLM-Wiki`** にフォールバックする。よって C ドライブだけの PC でも問題なく動く。
```powershell
.\install.bat                                  # ダイアログで選ぶ（D: 等も選択可）
.\install.bat -VaultRoot "C:\work\LLM-Wiki"    # 任意の場所へ直接指定
.\install.bat -NoPrompt                        # → C:\Users\<user>\Documents\LLM-Wiki
```
`hooks/hooks.json` も `${CLAUDE_PLUGIN_ROOT}` 相対で書かれているため、ドライブ依存箇所はない。

> ⚠ 個人の `~\.claude\CLAUDE.md` に vault パスを直書きしていると、そこだけ特定PC依存になる。
> **v0.2 以降は書く必要がない** — 解決済み vault パスと蓄積方針は SessionStart フック（`bootstrap.py`）が
> 毎セッション context に注入する（2.9）。既に直書きしている場合は削除してよい。

### 2.8 インストール後は **Claude Code を再起動**（重要）
`install.bat` が成功しても、**すでに起動している Claude Code には反映されない**。

- プラグインの `vault_root`（userConfig）はセッション起動時に読まれる
- `LLM_WIKI_VAULT_ROOT` は `setx` で設定するので**既存プロセスには届かない**

この2つが両方空だと、skill が vault を解決できず
**「Vault が未設定で inbox の場所が解決できない」**というエラーになる。

インストール後の確認手順:
```powershell
claude plugin list          # llm-wiki@llm-wiki-marketplace が enabled であること
```
Claude Code を**完全終了**（デスクトップアプリはタスクトレイ常駐に注意）して起動し直し、
`/llm-wiki:lint` が動けば成功。

登録されていなかった場合は手動で:
```powershell
claude plugin marketplace add <このリポジトリのパス or GitHub URL>
claude plugin install llm-wiki@llm-wiki-marketplace --config "vault_root=<vaultパス>"
```

> ⚠ **claude CLI が無いPCでは、install.ps1 はプラグイン登録をスキップする**。
> vault フォルダだけ作られて「完了」と表示されるため成功したように見えるが、
> GUI 登録（2.6）で `vault_root` を入れるまで skill は vault を解決できない。

### 2.9 蓄積方針はプラグインが配る（v0.2 以降・設定不要）

「自動蓄積」は 2 つの部品の組み合わせで成立する。**片方だけでは空回りする。**

| 部品 | 役割 |
|---|---|
| Stop フック `save_learnings.py` | 当日 `inbox/{日付}-{プロジェクト}.md` の**空の足場**を用意 |
| SessionStart フック `bootstrap.py` | 「いつ・何を・どこへ書くか」の**蓄積方針を context に注入** |

v0.1 では方針が各利用者の `~\.claude\CLAUDE.md` にしか無く、新規インストールでは
**毎日空のスタブが生成されるだけで誰も埋めない**状態だった。v0.2 でプラグイン側から配る。

注入される内容（`bootstrap.py` の `POLICY`）:

- 解決済み vault パスと、当日の追記先ファイル名
- 記録トリガー → 配置先（concepts / notes / pages）
- 書き方のルール（見出しに種別を明記／コード例を含める／wikilink と backtick の使い分け／
  **資格情報は伏せ字化する**）
- skill 一覧

**利用者は `~\.claude\CLAUDE.md` に何も書かなくてよい。** 方針を変えたい場合は
`plugins/llm-wiki/scripts/bootstrap.py` の `POLICY` を編集して再発行する
（毎セッション context に載るため行数は最小限に）。

インストーラは `--quiet-policy` 付きで `bootstrap.py` を呼ぶので、導入ログには方針が出ない。

---

## ③ 解説（仕組みと使い方）

### 3.1 全体構成
```
[Claude Code + プラグイン]                 [vault（あなたの知識・Obsidianで開く）]
  skills  init/save/ingest/query/lint   ──▶  concepts/ notes/ pages/ qa/
  hooks   SessionStart=bootstrap             inbox/  … 自動蓄積＋資料の投入口
          (足場生成＋蓄積方針の注入)                   (pptx/xlsx/pdf も置ける)
          Stop=save_learnings(当日足場)
  scripts lint.py / index.py /               sources/… 生ログ保全
          bootstrap.py / save_learnings.py            _attachments/ … 変換元の原本
          convert_inbox.py                   meta/   … index.md(自動生成) log rules
                                                       lint-ignore.txt template
                                             _proposals/ … 提案(将来)
        userConfig: vault_root ───────────────┘（このパスで両者が結びつく）
```

| コンポーネント | 役割 |
|---|---|
| skill `init` | vault の足場を生成（bootstrap 呼出） |
| skill `save` | 直前の会話の知見をページ化 |
| skill `ingest` | inbox の取り込み（Phase 0 変換 → A/B・完了マーカー） |
| skill `query` | Wiki を段階検索して出典付き回答 |
| skill `lint` | 健全性検査＋index 再生成 |
| hook SessionStart | `bootstrap.py`：フォルダ構成を冪等生成 |
| hook Stop | `save_learnings.py`：当日足場を用意＋過去日の空スタブ掃除 |
| script `lint.py` | 赤リンク/孤立/空/frontmatter/inbox を機械検出（exit code） |
| script `index.py` | 各ページ frontmatter から index.md を自動生成 |
| script `convert_inbox.py` | inbox の pptx/xlsx/docx/pdf/txt 等を md 化（原本は `sources/_attachments/` へ） |

### 3.2 設定項目
| 項目 | 内容 |
|---|---|
| `vault_root`（userConfig） | Wiki 一式の保存先。インストール時に設定。スクリプトへは環境変数 `CLAUDE_PLUGIN_OPTION_VAULT_ROOT` として渡る |
| `LLM_WIKI_VAULT_ROOT`（環境変数） | スタンドアロンで scripts を叩く時のフォールバック（install.ps1 が `setx` で設定） |
| hooks | SessionStart=bootstrap / Stop=save_learnings（`plugins/llm-wiki/hooks/hooks.json`） |
| `meta/lint-ignore.txt` | 意図的に残す赤リンク（将来ページ化予定）を1行1件で許容 |

スクリプト単体実行：
```
python plugins/llm-wiki/scripts/bootstrap.py "D:/資料/LLM-Wiki"
python plugins/llm-wiki/scripts/lint.py       "D:/資料/LLM-Wiki"
python plugins/llm-wiki/scripts/index.py      "D:/資料/LLM-Wiki"
```

### 3.3 日常の使い方
- 普通に開発する → Stopフックが `inbox/{日付}-{PJ}.md` に足場を用意（知見はここに追記されていく）
- `/llm-wiki:save` … 会話の知見を concepts/notes/pages へ整理
- `/llm-wiki:ingest` … inbox をまとめてページ化（Phase A/B）
- `/llm-wiki:query` … Wiki を検索して回答
- `/llm-wiki:lint` … 壊れチェック＋index 再生成（変更後は必ず）

frontmatter（全ページ）:
```yaml
---
type: concept | note | page | qa | synthesis | source
genre: <ジャンル>        # index のグルーピングキー
summary: "1行要約"        # index にそのまま出る
tags: []
related: ["[[関連]]"]
source: "PJ名/ファイル or URL"
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### 3.4 既存資料の Wiki 化（inbox に置いて ingest）
過去に書いた資料・メモを取り込むときは、**`inbox/` に置いて `/llm-wiki:ingest` を叩くだけ**。
pptx・xlsx・docx・pdf などもそのまま置ける（自動で md に変換される）。

1. `<vault>/inbox/` にファイルを置く（形式は下表）
2. Claude Code で `/llm-wiki:ingest`（「inbox を処理して」でも起動）
3. **Phase 0**: `convert_inbox.py` が非 md を md へ変換し、**原本は `sources/_attachments/` へ退避**
4. Phase A: 種別分類 → 原文を `sources/<genre>/` へ移動（**本文は無加工**、frontmatter だけ付与）
5. Phase B: `concepts/ notes/ pages/` の既存ページを検索し、あれば統合更新・無ければ新規作成。`[[リンク]]`＋frontmatter を付ける
6. 全部終わった**最後にだけ**ソースへ `type: source` を立てる → 途中で落ちても再実行で続行、二重取り込みなし
7. 仕上げに `index.py` 再生成＋`lint.py`（inbox が空・exit 0 になるまでクローズしない）

#### 対応形式

| 形式 | 変換内容 | 必要なライブラリ |
|---|---|---|
| `.md` | そのまま | — |
| `.txt` `.log` `.json` `.yml` | 本文そのまま（**cp932 の日本語も自動判別**） | — |
| `.csv` `.tsv` | markdown table | — |
| `.html` `.htm` | タグ除去（script/style は捨てる） | — |
| `.docx` | 見出し階層＋段落＋表を markdown 化 | python-docx |
| `.xlsx` `.xlsm` | シートごとに markdown table（**数式でなく値**を取る） | openpyxl |
| `.pptx` | スライドごとにテキスト＋表＋発表者ノート | python-pptx |
| `.pdf` | ページごとにテキスト抽出 | pypdf |
| `.doc` `.xls` `.ppt` | **非対応**。`.docx` 等で保存し直す | — |

ライブラリは `install.bat` が自動で `pip install` する。未導入でも上4行の形式は変換でき、
**PDF はライブラリ無しでも ingest 時に Claude が直接読み取れる**（Read が PDF ネイティブ対応のため）。
手で入れる場合:
```
pip install python-docx openpyxl python-pptx pypdf
```

単体実行（Claude を介さず変換だけしたい場合）:
```
python plugins/llm-wiki/scripts/convert_inbox.py "<vaultパス>"
```

注意点:
- 変換後の md は `inbox/<元の名前>.md`。**同名 md が既にあれば `-1` と採番**し、既存は絶対に上書きしない
- xlsx は 1 シート 2000 行、PDF は 300 ページで打ち切る（打ち切った旨を md 内と実行ログの両方に明記）
- 0byte・中身なしスタブは取り込まず削除される（自動蓄積フックの空足場対策）
- ファイル名は自由（自動蓄積分の慣習は `{YYYY-MM-DD}-{プロジェクト名}.md`）
- **フォルダごと置いても取り込まれない**。対象は `inbox/` 直下のファイルだけ。フォルダは変換もされず lint が末尾 `/` 付きで「未変換」として報告する
- 大量にあるときは**ジャンル単位で小分け**投入が安全。既存ページとの統合判断の精度が上がる

### 3.5 更新・発行

プラグインのキャッシュは **version 単位**で作られる（`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`）。
version を据え置いたまま push すると、利用者側は `marketplace update` しても**古いコードのまま**になる。

1. 中身を直す
2. **version を2箇所とも上げる**（同じ値にすること）
   - `plugins/llm-wiki/.claude-plugin/plugin.json` の `version`
   - `.claude-plugin/marketplace.json` の該当プラグインの `version`
3. `.\publish.bat "変更内容"` → GitHub へ push
   （`tools/check_version.py` が「2箇所の一致」と「`plugins/` に差分があるのに据え置き」を検査して止める）
4. 各ユーザー側の更新：`/plugin marketplace update llm-wiki-marketplace` → **Claude Code を再起動**
5. 反映確認：`claude plugin list` の version、または
   `~/.claude/plugins/installed_plugins.json` の `version` が上がっていること

### 3.6 注意点・トラブルシュート
| 症状 | 原因・対処 |
|---|---|
| `.bat` が「指定されたファイルが見つかりません」 | .bat は **ASCII＋CRLF** 必須。UTF-8/LF だと cmd.exe が誤動作 |
| プラグインが `failed to load: Duplicate hooks` | plugin.json に `hooks`/`skills` を書かない（標準dirが自動ロード） |
| 同じ inbox に空スタブが二重生成 | 旧 global Stopフック（`~/.claude/hooks/save_learnings.py`）を settings.json から外す |
| Python 導入直後に `python` が見つからない | 新しいシェルを開くか、`-InstallPython` 経由なら同一セッションで PATH 再読込済み |
| **蓄積方針が出ない／inbox に当日ファイルができない** | フック（`hooks.json`）は `python` を直接呼ぶ。`py` ランチャーしか無い・Microsoft Store のエイリアスが横取りしている PC では SessionStart/Stop が黙って失敗する。`install.bat -InstallPython` で PATH 付き Python を入れるか、`python.exe` を PATH に通す（設定 > アプリ > アプリ実行エイリアス で `python.exe` を OFF）。インストーラが検出して警告する |
| private repo で `marketplace add` 失敗 | 各PCで `gh auth login`＋`gh auth setup-git`、HTTPSはフルURL指定 |
| private + HTTPS で自動更新されない | 背景更新は認証が効かない。手動 `marketplace update`／SSH運用／`CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE=1` |
| lint が当日 inbox スタブを挙げる | 「想定内」区分で失敗に数えない。翌日フックが自動掃除 |
| **「Vault が未設定で inbox の場所が解決できない」** | vault の解決経路が両方空。①`claude plugin list` に `llm-wiki@llm-wiki-marketplace` が居るか確認 → 無ければ再インストール ②**Claude Code を完全終了して再起動**（`setx` も userConfig も起動済みプロセスには届かない）。詳細は 2.8 |
| インストーラは「完了」と出たのに skill が vault を見つけない | CLI が無い環境では install.ps1 が**プラグイン登録をスキップ**する（vault フォルダだけ作って完了する）。GUI 登録（2.6）で `vault_root` を必ず入力する |
| pptx/xlsx/docx が「未導入でスキップ」される | 変換ライブラリが無い。`pip install python-docx openpyxl python-pptx pypdf`（3.4）。オフライン環境なら install 時に `-NoDocLibs` |
| lint に「inbox 未変換ファイル」が出る | 非 md が残っている。`convert_inbox.py` を実行。`.doc/.xls/.ppt` は `.docx` 等で保存し直す |
| 移行先PCに D ドライブが無い | D ドライブは不要。`vault_root` を任意パスに（既定 `~\Documents\LLM-Wiki`）。`~\.claude\CLAUDE.md` に直書きしたパスは要書き換え（2.7） |

---

## ④ 全社展開

**前提**: LLM Wiki は**ファイルベース**（DB もサーバーデーモンも持たない）。「全社でサーバー運用」は目的によって手段が4つに分かれる。

### ① プラグインの配布を全社化 — 一番簡単
社内 **GitHub Enterprise / 社内Git** に marketplace を置けば、全員が同じ仕組みを入れられる。「サーバーに置く」の最小形。
```
/plugin marketplace add <社内>/llm-wiki-marketplace
/plugin install llm-wiki@llm-wiki-marketplace
```

### ② 共有ナレッジベース化（みんなで1つのWikiを育てる） — 現実解あり
vault 自体を **git 管理の中央リポジトリ**にして共有するのが定石（Obsidian Git 方式）。
- 各自の `vault_root` を自分のクローンに向ける → 書いたら commit/push、朝 pull
- サーバー側（社内Git）が正本を保持
- **同時編集はマージ運用**。リアルタイム多人数同時書き込みには非対応（ファイルなので競合する）
- 本プラグインの **lint・index自動生成・`type:source`完了マーカー**が競合と破損をかなり減らす

代替：ネットワーク共有(SMB)や OneDrive/SharePoint 同期でも可能だが、同時書き込みで上書き事故が起きやすいため **git 推奨**。

### ③ サーバー側で無人自動化 — 可能
`lint.py` / `index.py` / `bootstrap.py` は**素のPython**なので、サーバーの cron / CI で回せる（Claude Code 不要）。
- 夜間に index 再生成・健全性チェック（壊れたら Slack 通知等）
- vault を静的サイト化して社内ブラウザ閲覧に公開
- さらに踏み込むなら **headless の `claude -p`** をサーバーで定期実行し、inbox の ingest や curiosity（休眠ページの自己点検）を無人で回す構成も可能（※各実行がAPI/サブスクを消費、サーバー側のClaude認証が必要）

### ④ ホスト型 Wiki サービス（ACL・全文検索・同時編集） — 素ではムリ
Confluence のような多人数同時・権限管理・検索付きの Web サービスとしては、そのままでは動かない。
要件なら vault の上に **Webビューア or DB化レイヤー**を別途載せる別プロジェクトになる。

### ⚠ 全社運用で必須のガバナンス設計
- **個人vault と 共有vault を分ける**（全員の生の学びがそのまま全社に見えるのは危険）。個人inbox → 選別して共有へ、が安全。
- **秘密情報の混入防止**：自動蓄積フックがパスワード・接続文字列等を共有vaultに載せないルール／フィルタ。
- **粒度と重複**：全社だと同義ページが乱立しやすい。lint の孤立・弱関連検出や（将来の）curiosity で統制。

### 現実的なおすすめ構成（全社なら）
1. **配布**：社内Gitに marketplace（①）
2. **共有vault**：git-backed の中央リポ、各自クローン、個人vaultと分離（②）
3. **サーバー自動化**：CIで nightly の index再生成＋lint＋静的サイト公開（③）
4. ④のホスト型が欲しくなったら、その時に別レイヤーを検討

**結論**: 配布と自動化はサーバーで全社化できる。共有ナレッジ化も git 運用なら実用的。ただし**リアルタイム多人数のホスト型Wikiサービスではない**。
