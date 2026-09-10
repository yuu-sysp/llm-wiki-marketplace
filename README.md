# llm-wiki-marketplace

ハイブリッド **LLM Wiki** を Claude Code プラグインとして配布するマーケットプレイス。
新規PCに「仕組み＋空 vault のフォルダ構成」までインストーラ1本で用意できる。

**知見の蓄積方針（いつ・何を・どこへ書くか）はプラグインが配る。** SessionStart フックが
解決済みの vault パスと方針を毎セッション注入するので、利用者の `~/.claude/CLAUDE.md` に
何も書かなくてよい（特定PC依存にならない）。

## 中身

- `plugins/llm-wiki/` … プラグイン本体（skills / hooks / scripts / templates）
- `install.ps1` / `install.bat` … 新規PC導入用インストーラ
- `publish.bat` … このリポジトリを GitHub へ発行（version の整合チェック付き）
- `tools/check_version.py` … 発行前の version 検査（2つの manifest の一致・bump 忘れ）
- `docs/setup-guide.md` / `.html` … セットアップ資料（ねらい／導入／解説／全社展開）
- `.claude-plugin/marketplace.json` … マーケットプレイス定義

## 発行（あなたのPC）

プラグインの中身を直したら、**先に version を上げる**。プラグインのキャッシュは version 単位で
作られるため、据え置きのまま push しても利用者側は古いコードのまま更新されない。

1. `plugins/llm-wiki/.claude-plugin/plugin.json` の `version`
2. `.claude-plugin/marketplace.json` の該当プラグインの `version`

の**2箇所**を同じ値に上げてから発行する（`publish.bat` が一致と bump を検査して止める）。

```
git remote add origin https://github.com/yuu-sysp/llm-wiki-marketplace.git   # 初回のみ
publish.bat  "変更内容"      # メッセージは必ずダブルクォートで囲む
```

導入済みPCの更新は `/plugin marketplace update llm-wiki-marketplace`。

## 導入（新規PC）

### 方法A: インストーラ（推奨・フォルダ構成まで自動）

リポジトリを取得して:
```
git clone https://github.com/yuu-sysp/llm-wiki-marketplace.git
cd llm-wiki-marketplace
install.bat                                # 保存先はフォルダ選択ダイアログで指定
install.bat -VaultRoot "D:\資料\LLM-Wiki"  # パスを直接指定する場合
```
インストーラが Python チェック → プラグイン登録（claude CLI があれば）→ vault のフォルダ構成生成 → 初期 lint まで実行する。

`-VaultRoot` 省略時は**エクスプローラー風のフォルダ選択ダイアログ**が開く（ダブルクリック起動でも同じ）。
D: 等の別ドライブも選べ、選んだフォルダ直下に `LLM-Wiki` を作る。無人実行は `-NoPrompt`（既定 `~\Documents\LLM-Wiki`）。

インストール後は **Claude Code を完全終了して再起動**すること（起動済みセッションには vault_root が反映されない）。
詳細は `docs/setup-guide.md` の 2.4 / 2.7 / 2.8 を参照。

### 方法B: Claude Code 内から

```
/plugin marketplace add yuu-sysp/llm-wiki-marketplace
/plugin install llm-wiki@llm-wiki-marketplace
```
インストール時に vault 保存先を尋ねられる。フォルダ構成は初回セッションの SessionStart フック（bootstrap）が自動生成する。

## 使い方（導入後）

Claude Code で:
- `/llm-wiki:init` … vault 初期化（手動再生成）
- `/llm-wiki:save` … 会話の知見をページ化
- `/llm-wiki:ingest` … inbox 取り込み（Phase A/B）
- `/llm-wiki:query` … Wiki 検索
- `/llm-wiki:lint` … 健全性検査＋index 再生成

詳細は `plugins/llm-wiki/README.md` を参照。

## 前提

- Python 3 が PATH にあること（scripts が Python）
- プラグイン登録には Claude Code（`claude` CLI）が必要
