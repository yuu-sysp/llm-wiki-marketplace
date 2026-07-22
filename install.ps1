<#
  LLM Wiki 導入インストーラ（新規PC用）

  やること:
    1. Python の存在チェック（無ければ中断）
    2. claude CLI チェック（有ればプラグイン登録、無ければ警告して手動案内）
    3. vault パス決定（引数 or 既定 ~\Documents\LLM-Wiki）
    4. プラグインをマーケットプレイス登録＋インストール（vault を userConfig で渡す）
    5. bootstrap.py で vault のフォルダ構成＋meta雛形を冪等生成
    6. LLM_WIKI_VAULT_ROOT 環境変数を設定（スタンドアロン実行のフォールバック用）

  使い方:
    powershell -ExecutionPolicy Bypass -File install.ps1 [-VaultRoot <path>] [-Marketplace <path|owner/repo>]
    例) install.ps1 -VaultRoot "D:\資料\LLM-Wiki"
#>
param(
  [string]$VaultRoot = "",
  [string]$Marketplace = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
if (-not $Marketplace) { $Marketplace = $RepoRoot }          # 既定はこのリポジトリ自身（ローカル）
if (-not $VaultRoot)   { $VaultRoot = Join-Path $HOME "Documents\LLM-Wiki" }

Write-Host "=== LLM Wiki インストーラ ===" -ForegroundColor Cyan
Write-Host ("vault      : {0}" -f $VaultRoot)
Write-Host ("marketplace: {0}" -f $Marketplace)
Write-Host ""

# 1) Python チェック
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
  Write-Host "[NG] Python が見つかりません。" -ForegroundColor Red
  Write-Host "     https://www.python.org/downloads/ から Python 3 を入れて PATH を通してから再実行してください。"
  exit 1
}
Write-Host ("[OK] Python: {0}" -f (& python --version 2>&1))

# 2) claude CLI チェック
$claude = Get-Command claude -ErrorAction SilentlyContinue
$havePluginCli = $false
if ($claude) {
  Write-Host ("[OK] claude CLI: {0}" -f (& claude --version 2>&1))
  $havePluginCli = $true
} else {
  Write-Host "[!!] claude CLI が見つかりません。プラグイン登録はスキップし、フォルダ構成のみ作成します。" -ForegroundColor Yellow
}

# 3) プラグイン登録（claude がある場合のみ）
if ($havePluginCli) {
  Write-Host "`n--- プラグイン登録 ---"
  & claude plugin marketplace add "$Marketplace"
  if ($LASTEXITCODE -ne 0) { Write-Host "[!!] marketplace add に失敗（既登録なら無視可）" -ForegroundColor Yellow }
  & claude plugin install "llm-wiki@llm-wiki-marketplace" --config "vault_root=$VaultRoot"
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[!!] plugin install が失敗しました。バージョンにより CLI 書式が異なる場合があります。" -ForegroundColor Yellow
    Write-Host "     Claude Code 内で次を実行してください:"
    Write-Host "       /plugin marketplace add $Marketplace"
    Write-Host "       /plugin install llm-wiki@llm-wiki-marketplace"
  }
}

# 4) フォルダ構成＋meta雛形の生成（bootstrap は冪等）
Write-Host "`n--- vault 生成 ---"
& python (Join-Path $RepoRoot "plugins\llm-wiki\scripts\bootstrap.py") "$VaultRoot"

# 5) 環境変数（スタンドアロン実行のフォールバック）
setx LLM_WIKI_VAULT_ROOT "$VaultRoot" | Out-Null
Write-Host "[OK] 環境変数 LLM_WIKI_VAULT_ROOT を設定（新しいシェルから有効）"

# 6) 初期 lint
Write-Host "`n--- 初期 lint ---"
$env:LLM_WIKI_VAULT_ROOT = $VaultRoot
& python (Join-Path $RepoRoot "plugins\llm-wiki\scripts\lint.py") "$VaultRoot"

Write-Host "`n=== 完了 ===" -ForegroundColor Green
Write-Host ("vault: {0}" -f $VaultRoot)
if (-not $havePluginCli) {
  Write-Host "※ claude CLI 未導入のため、プラグインは未登録です。Claude Code 導入後に本スクリプトを再実行してください。"
}
