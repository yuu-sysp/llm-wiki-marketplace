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

### 2.1 前提
- **Python 3** が PATH にある（scripts が Python）。無い場合はインストーラの `-InstallPython` で自動導入可（2.5）。
- **Claude Code**：CLI か **デスクトップアプリ**のどちらか。プラグイン登録に必要（登録方法は下記）。
- （private リポジトリから入れる場合）GitHub 認証

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
.\install.bat -VaultRoot "D:\資料\LLM-Wiki"
```
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

---

## ③ 解説（仕組みと使い方）

### 3.1 全体構成
```
[Claude Code + プラグイン]                 [vault（あなたの知識・Obsidianで開く）]
  skills  init/save/ingest/query/lint   ──▶  concepts/ notes/ pages/ qa/
  hooks   SessionStart=bootstrap             inbox/  … 自動蓄積の受け皿
          Stop=save_learnings                sources/… 生ログ保全
  scripts lint.py / index.py /               meta/   … index.md(自動生成) log rules
          bootstrap.py / save_learnings.py           lint-ignore.txt template
                                             _proposals/ … 提案(将来)
        userConfig: vault_root ───────────────┘（このパスで両者が結びつく）
```

| コンポーネント | 役割 |
|---|---|
| skill `init` | vault の足場を生成（bootstrap 呼出） |
| skill `save` | 直前の会話の知見をページ化 |
| skill `ingest` | inbox の取り込み（Phase A/B・完了マーカー） |
| skill `query` | Wiki を段階検索して出典付き回答 |
| skill `lint` | 健全性検査＋index 再生成 |
| hook SessionStart | `bootstrap.py`：フォルダ構成を冪等生成 |
| hook Stop | `save_learnings.py`：当日足場を用意＋過去日の空スタブ掃除 |
| script `lint.py` | 赤リンク/孤立/空/frontmatter/inbox を機械検出（exit code） |
| script `index.py` | 各ページ frontmatter から index.md を自動生成 |

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
type: concept | note | page | synthesis | source
genre: <ジャンル>        # index のグルーピングキー
summary: "1行要約"        # index にそのまま出る
tags: []
related: ["[[関連]]"]
source: "PJ名/ファイル or URL"
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### 3.4 更新・発行
- プラグインを直したら（開発PC）：`.\publish.bat "変更内容"` → GitHub へ push
- 各ユーザー側の更新：`/plugin marketplace update llm-wiki-marketplace`

### 3.5 注意点・トラブルシュート
| 症状 | 原因・対処 |
|---|---|
| `.bat` が「指定されたファイルが見つかりません」 | .bat は **ASCII＋CRLF** 必須。UTF-8/LF だと cmd.exe が誤動作 |
| プラグインが `failed to load: Duplicate hooks` | plugin.json に `hooks`/`skills` を書かない（標準dirが自動ロード） |
| 同じ inbox に空スタブが二重生成 | 旧 global Stopフック（`~/.claude/hooks/save_learnings.py`）を settings.json から外す |
| Python 導入直後に `python` が見つからない | 新しいシェルを開くか、`-InstallPython` 経由なら同一セッションで PATH 再読込済み |
| private repo で `marketplace add` 失敗 | 各PCで `gh auth login`＋`gh auth setup-git`、HTTPSはフルURL指定 |
| private + HTTPS で自動更新されない | 背景更新は認証が効かない。手動 `marketplace update`／SSH運用／`CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE=1` |
| lint が当日 inbox スタブを挙げる | 「想定内」区分で失敗に数えない。翌日フックが自動掃除 |

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
