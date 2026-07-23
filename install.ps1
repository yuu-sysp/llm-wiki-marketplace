<#
  LLM Wiki 導入インストーラ（新規PC用 / Windows）

  やること:
    1. Python 検出。無ければ -InstallPython 指定時に自動インストール（winget→python.org、PATH登録込み）
    2. claude CLI 検出（有ればプラグイン登録、無ければデスクトップアプリGUIでの登録手順を案内）
    3. vault パス決定（引数 or 既定 ~\Documents\LLM-Wiki）
    4. プラグインをマーケットプレイス登録＋インストール（vault を userConfig で渡す）
    5. bootstrap.py で vault のフォルダ構成＋meta雛形を冪等生成
    6. LLM_WIKI_VAULT_ROOT 環境変数を設定（スタンドアロン実行のフォールバック用）
    7. 初期 lint

  使い方:
    powershell -ExecutionPolicy Bypass -File install.ps1 [-VaultRoot <path>] [-Marketplace <path|owner/repo>] [-InstallPython]
    例) install.ps1 -VaultRoot "D:\資料\LLM-Wiki" -InstallPython
#>
param(
  [string]$VaultRoot = "",
  [string]$Marketplace = "",
  [switch]$InstallPython
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
if (-not $Marketplace) { $Marketplace = $RepoRoot }          # 既定はこのリポジトリ自身（ローカル）
if (-not $VaultRoot)   { $VaultRoot = Join-Path $HOME "Documents\LLM-Wiki" }

Write-Host "=== LLM Wiki インストーラ ===" -ForegroundColor Cyan
Write-Host ("vault      : {0}" -f $VaultRoot)
Write-Host ("marketplace: {0}" -f $Marketplace)
Write-Host ""

# ---- ヘルパー: 現在セッションの PATH をユーザ/マシン両方から再読込 ----
function Update-SessionPath {
  $machine = [Environment]::GetEnvironmentVariable("PATH", "Machine")
  $user    = [Environment]::GetEnvironmentVariable("PATH", "User")
  $env:PATH = ($machine, $user | Where-Object { $_ }) -join ";"
}

# ---- ヘルパー: python 実行コマンドを解決（python / py の順） ----
function Resolve-Python {
  Update-SessionPath
  foreach ($c in @("python", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
      try {
        $v = & $c --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$v" -match "Python 3") { return $c }
      } catch {}
    }
  }
  return $null
}

# ---- ヘルパー: Python 自動インストール（winget→python.org） ----
function Install-Python3 {
  Write-Host "--- Python 自動インストール ---"
  $winget = Get-Command winget -ErrorAction SilentlyContinue
  if ($winget) {
    Write-Host "[..] winget で Python.Python.3.12 を導入します（PATH登録込み）"
    & winget install --id Python.Python.3.12 -e --scope user `
        --accept-source-agreements --accept-package-agreements
    Update-SessionPath
    if (Resolve-Python) { return $true }
    Write-Host "[!!] winget 後も python を解決できません。python.org へフォールバックします。" -ForegroundColor Yellow
  } else {
    Write-Host "[!!] winget が見つかりません。python.org へフォールバックします。" -ForegroundColor Yellow
  }

  # フォールバック: python.org 公式インストーラ（/quiet PrependPath=1 で PATH 登録）
  try {
    $ver = "3.12.7"
    $url = "https://www.python.org/ftp/python/$ver/python-$ver-amd64.exe"
    $out = Join-Path $env:TEMP "python-$ver-amd64.exe"
    Write-Host "[..] ダウンロード: $url"
    Invoke-WebRequest -Uri $url -OutFile $out
    Write-Host "[..] サイレントインストール（PrependPath=1）"
    Start-Process -FilePath $out -Wait -ArgumentList @(
      "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1"
    )
    Update-SessionPath
    return [bool](Resolve-Python)
  } catch {
    Write-Host ("[NG] python.org インストールに失敗: {0}" -f $_.Exception.Message) -ForegroundColor Red
    return $false
  }
}

# ============ 1) Python 検出／自動インストール ============
$PY = Resolve-Python
if (-not $PY) {
  if ($InstallPython) {
    if (Install-Python3) {
      $PY = Resolve-Python
    }
  }
}
if (-not $PY) {
  Write-Host "[NG] Python が見つかりません。" -ForegroundColor Red
  Write-Host "     自動導入するには -InstallPython を付けて再実行してください:"
  Write-Host "       install.bat -VaultRoot `"$VaultRoot`" -InstallPython"
  Write-Host "     もしくは https://www.python.org/downloads/ から手動導入（PATH追加）してください。"
  exit 1
}
Write-Host ("[OK] Python: {0}  ({1})" -f (& $PY --version 2>&1), $PY)

# ============ 2) claude CLI 検出 ============
$claude = Get-Command claude -ErrorAction SilentlyContinue
$havePluginCli = [bool]$claude
if ($havePluginCli) {
  Write-Host ("[OK] claude CLI: {0}" -f (& claude --version 2>&1))
} else {
  Write-Host "[!!] claude CLI が見つかりません（デスクトップアプリのみ環境）。" -ForegroundColor Yellow
  Write-Host "     プラグイン登録は後述のGUI手順で行います。フォルダ構成はこのまま作成します。"
}

# ============ 3) プラグイン登録（claude がある場合のみ） ============
if ($havePluginCli) {
  Write-Host "`n--- プラグイン登録 ---"
  & claude plugin marketplace add "$Marketplace"
  if ($LASTEXITCODE -ne 0) { Write-Host "[!!] marketplace add に失敗（既登録なら無視可）" -ForegroundColor Yellow }
  & claude plugin install "llm-wiki@llm-wiki-marketplace" --config "vault_root=$VaultRoot"
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[!!] plugin install が失敗しました。Claude Code 内で次を実行してください:" -ForegroundColor Yellow
    Write-Host "       /plugin marketplace add $Marketplace"
    Write-Host "       /plugin install llm-wiki@llm-wiki-marketplace"
  }
}

# ============ 4) フォルダ構成＋meta雛形（bootstrap は冪等） ============
Write-Host "`n--- vault 生成 ---"
& $PY (Join-Path $RepoRoot "plugins\llm-wiki\scripts\bootstrap.py") "$VaultRoot"

# ============ 5) 環境変数（スタンドアロン実行のフォールバック） ============
setx LLM_WIKI_VAULT_ROOT "$VaultRoot" | Out-Null
Write-Host "[OK] 環境変数 LLM_WIKI_VAULT_ROOT を設定（新しいシェルから有効）"

# ============ 6) 初期 lint ============
Write-Host "`n--- 初期 lint ---"
$env:LLM_WIKI_VAULT_ROOT = $VaultRoot
& $PY (Join-Path $RepoRoot "plugins\llm-wiki\scripts\lint.py") "$VaultRoot"

# ============ 7) 完了メッセージ ============
Write-Host "`n=== 完了 ===" -ForegroundColor Green
Write-Host ("vault: {0}" -f $VaultRoot)
if (-not $havePluginCli) {
  Write-Host ""
  Write-Host "▼ デスクトップアプリでプラグインを登録する手順（CLI不要）:" -ForegroundColor Cyan
  Write-Host "  1. アプリのプロンプト横の [＋] → Plugins（または chat に /plugin と入力）"
  Write-Host "  2. Marketplaces タブ → Add marketplace → 次を貼付:"
  Write-Host "       $Marketplace"
  Write-Host "     （GitHub から入れる場合は https://github.com/yuu-sysp/llm-wiki-marketplace.git）"
  Write-Host "  3. Discover タブ → llm-wiki を選び Install → スコープ User"
  Write-Host ("     → vault_root に `"{0}`" を入力して Confirm" -f $VaultRoot)
  Write-Host "  4. /reload-plugins でリロード（/llm-wiki:init 等が出れば成功）"
  Write-Host ""
  Write-Host "  CLI も入れたい場合（依存なし・自動更新・管理者権限不要）:"
  Write-Host "     irm https://claude.ai/install.ps1 | iex"
}
