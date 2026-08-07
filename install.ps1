<#
  LLM Wiki 導入インストーラ（新規PC用 / Windows）

  やること:
    1. Python 検出。無ければ -InstallPython 指定時に自動インストール（winget→python.org、PATH登録込み）
    1.5 inbox 変換ライブラリを pip 導入（-NoDocLibs で省略可。失敗しても続行）
    2. claude CLI 検出（有ればプラグイン登録、無ければデスクトップアプリGUIでの登録手順を案内）
    3. vault パス決定（引数 → GUIフォルダ選択 → 既定 ~\Documents\LLM-Wiki）
    4. プラグインをマーケットプレイス登録＋インストール（vault を userConfig で渡す）
    5. bootstrap.py で vault のフォルダ構成＋meta雛形を冪等生成
    6. LLM_WIKI_VAULT_ROOT 環境変数を設定（スタンドアロン実行のフォールバック用）
    7. 初期 lint

  使い方:
    powershell -ExecutionPolicy Bypass -File install.ps1 [-VaultRoot <path>] [-Marketplace <path|owner/repo>] [-InstallPython] [-NoPrompt]
    例) install.ps1 -VaultRoot "D:\資料\LLM-Wiki" -InstallPython

  -VaultRoot 省略時はエクスプローラー風のフォルダ選択ダイアログを出す（ドライブも選べる）。
  CI・無人実行は -VaultRoot を明示するか -NoPrompt を付ける（既定パスで進む）。
#>
param(
  [string]$VaultRoot = "",
  [string]$Marketplace = "",
  [switch]$InstallPython,
  [switch]$NoPrompt,         # ダイアログを出さず既定パスで進む（無人実行用）
  [switch]$NoDocLibs         # pptx/xlsx/docx/pdf 変換ライブラリの pip を省略（オフライン環境用）
)

$ErrorActionPreference = "Stop"

# 日本語出力の文字化け対策: コンソール入出力を UTF-8 に固定する。
# （このファイル自体は UTF-8 with BOM で保存し、Windows PowerShell 5.1 が
#   cmd/.bat 経由で cp932 と誤読するのを防ぐ。手動の文字コード変換は不要。）
try {
  $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {}
$RepoRoot = $PSScriptRoot
if (-not $Marketplace) { $Marketplace = $RepoRoot }          # 既定はこのリポジトリ自身（ローカル）
$DefaultVault = Join-Path $HOME "Documents\LLM-Wiki"

# ---- ヘルパー: フォルダ選択ダイアログ（キャンセル/利用不可なら $null） ----
# WinForms は STA スレッドでないと開けない（pwsh 7 は既定 MTA）。
# そのため apartment を見て、駄目なら apartment 非依存の Shell COM にフォールバックする。
function Select-VaultFolder {
  param([string]$Description, [string]$InitialPath)

  # 「キャンセルされた」と「そもそもダイアログを出せなかった」を呼び出し側で区別するため、
  # 表示に成功したかどうかを別途持つ（戻り値 $null だけでは判別できない）。
  $script:FolderPickerShown = $false
  $isSta = [Threading.Thread]::CurrentThread.GetApartmentState() -eq 'STA'
  if ($isSta) {
    try {
      Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
      $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
      $dlg.Description         = $Description
      $dlg.ShowNewFolderButton = $true
      # MyComputer を root にすると D: など全ドライブがツリーに出る
      $dlg.RootFolder          = [Environment+SpecialFolder]::MyComputer
      if ($InitialPath) { $dlg.SelectedPath = $InitialPath }
      $script:FolderPickerShown = $true
      $res = $dlg.ShowDialog()
      $picked = $dlg.SelectedPath
      $dlg.Dispose()
      if ($res -eq [System.Windows.Forms.DialogResult]::OK -and $picked) { return $picked }
      return $null                                  # キャンセル
    } catch {
      # WinForms が使えない環境（Server Core 等）は COM へ
      $script:FolderPickerShown = $false
    }
  }

  try {
    # BIF_RETURNONLYFSDIRS(0x1) | BIF_EDITBOX(0x10) | BIF_NEWDIALOGSTYLE(0x40)
    #   → リサイズ可・「新しいフォルダー」ボタン付き・パス直接入力可
    $shell  = New-Object -ComObject Shell.Application
    $script:FolderPickerShown = $true
    $folder = $shell.BrowseForFolder(0, $Description, 0x51)
    if ($folder -and $folder.Self.Path) { return $folder.Self.Path }
    return $null
  } catch {
    $script:FolderPickerShown = $false
    return $null                                    # GUI 不可（無人実行など）
  }
}

# ---- ヘルパー: 選んだフォルダから vault パスを決める ----
# インストーラの慣習に合わせ「置き場所（親）を選ぶ」形にする。
# 既に LLM-Wiki 自体を選んだ場合は二重にしない。
function Resolve-VaultPath {
  param([string]$Picked)
  if (-not $Picked) { return $null }
  $trimmed = $Picked.TrimEnd('\', '/')
  if ((Split-Path $trimmed -Leaf) -ieq 'LLM-Wiki') { return $trimmed }
  return (Join-Path $trimmed 'LLM-Wiki')
}

# ---- vault パス決定: 引数 → GUI選択 → 既定 ----
if (-not $VaultRoot) {
  if ($NoPrompt) {
    $VaultRoot = $DefaultVault
  } else {
    Write-Host "vault（Wiki の保存先）を選んでください。ダイアログを開きます..." -ForegroundColor Cyan
    Write-Host "  ※ 選んだフォルダの直下に LLM-Wiki フォルダを作ります（D: など別ドライブも選べます）"
    $picked = Select-VaultFolder -Description "LLM Wiki の保存先にする親フォルダを選んでください（直下に LLM-Wiki を作成します）" `
                                 -InitialPath (Split-Path $DefaultVault -Parent)
    if ($picked) {
      $VaultRoot = Resolve-VaultPath $picked
    } elseif ($FolderPickerShown) {
      # ダイアログを出せた上でのキャンセルは意思表示なので中止する（勝手な場所に作らない）
      Write-Host "[中止] フォルダが選択されませんでした。" -ForegroundColor Yellow
      Write-Host "       保存先を指定して再実行してください: install.bat -VaultRoot `"<path>`""
      Write-Host "       既定の $DefaultVault でよければ: install.bat -NoPrompt"
      exit 1
    } else {
      $VaultRoot = $DefaultVault                    # GUI 不可の無人実行 → 既定で続行
    }
  }
}

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

# ============ 1.5) 変換ライブラリ（inbox の pptx/xlsx/docx/pdf 対応） ============
# 失敗してもインストール全体は続行する。無くても txt/csv/html は変換でき、
# PDF は ingest 時に Claude が直接読めるため、ここで止める価値がない。
$docLibsOk = $false
if ($NoDocLibs) {
  Write-Host "[--] 変換ライブラリの導入をスキップします（-NoDocLibs）"
} else {
  Write-Host "`n--- 変換ライブラリ導入（inbox の pptx/xlsx/docx/pdf 用）---"
  & $PY -m pip install --user --upgrade python-docx openpyxl python-pptx pypdf
  $docLibsOk = ($LASTEXITCODE -eq 0)
  if ($docLibsOk) {
    Write-Host "[OK] python-docx / openpyxl / python-pptx / pypdf" -ForegroundColor Green
  } else {
    Write-Host "[!!] 変換ライブラリの導入に失敗しました（インストールは続行します）" -ForegroundColor Yellow
    Write-Host "     後で次を実行してください:"
    Write-Host "       $PY -m pip install --user python-docx openpyxl python-pptx pypdf"
    Write-Host "     未導入でも txt/csv/html/json は変換でき、PDF は ingest 時に Claude が直接読めます。"
  }
}

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
# vault_root は userConfig としてここで初めて保存される。ここが通らないと skill 側が
# vault を解決できず「Vault が未設定」になるため、成否を必ず検証して持ち回る。
$pluginRegistered = $false
if ($havePluginCli) {
  Write-Host "`n--- プラグイン登録 ---"
  & claude plugin marketplace add "$Marketplace"
  if ($LASTEXITCODE -ne 0) { Write-Host "[!!] marketplace add に失敗（既登録なら無視可）" -ForegroundColor Yellow }

  & claude plugin install "llm-wiki@llm-wiki-marketplace" --config "vault_root=$VaultRoot"
  $installExit = $LASTEXITCODE

  # 終了コードだけを信じず、実際の登録状態を正とする。
  # （導入済みの場合 install は "already installed" と出して 0 を返すが、--config は反映される）
  $listed = (& claude plugin list 2>&1 | Out-String)
  $pluginRegistered = [bool]($listed -match "llm-wiki@llm-wiki-marketplace")

  if ($pluginRegistered) {
    Write-Host "[OK] プラグイン登録＋vault_root 設定を確認" -ForegroundColor Green
    if ($installExit -ne 0) {
      Write-Host "[!!] install が非0終了でした。vault_root が反映されていない可能性があります" -ForegroundColor Yellow
    }
  } else {
    Write-Host "[NG] プラグイン登録に失敗しました（vault_root が未設定のままです）" -ForegroundColor Red
  }
}

# ============ 4) フォルダ構成＋meta雛形（bootstrap は冪等） ============
Write-Host "`n--- vault 生成 ---"
# --quiet-policy: 蓄積方針の出力は SessionStart フック用。インストーラのログには不要
& $PY (Join-Path $RepoRoot "plugins\llm-wiki\scripts\bootstrap.py") "$VaultRoot" --quiet-policy

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

# 再起動の告知は必須。plugin userConfig も setx した環境変数も、
# 「すでに起動している Claude Code」には反映されないため。
Write-Host ""
Write-Host "▼ 次にやること（必須）" -ForegroundColor Cyan
Write-Host "  ★ Claude Code を完全に終了して起動し直してください。"
Write-Host "    （起動済みのセッションには vault_root も環境変数も反映されません。"
Write-Host "      デスクトップアプリはタスクトレイに常駐している場合があるので終了しきること）"
Write-Host "  ・確認: claude plugin list  → llm-wiki@llm-wiki-marketplace が enabled であること"
Write-Host "  ・確認: Claude Code で /llm-wiki:lint が動けば成功"
if (-not $NoDocLibs -and -not $docLibsOk) {
  Write-Host "  ・変換ライブラリが未導入です。pptx/xlsx/docx を inbox で扱うには上記 pip を実行してください" -ForegroundColor Yellow
}

if ($havePluginCli -and -not $pluginRegistered) {
  Write-Host ""
  Write-Host "▼ プラグイン登録が失敗しています。次を手で実行してください:" -ForegroundColor Red
  Write-Host "     claude plugin marketplace add `"$Marketplace`""
  Write-Host ("     claude plugin install llm-wiki@llm-wiki-marketplace --config `"vault_root={0}`"" -f $VaultRoot)
  Write-Host "  これを行わないと skill が vault を解決できず"
  Write-Host "  「Vault が未設定で inbox の場所が解決できない」というエラーになります。" -ForegroundColor Yellow
}

if (-not $havePluginCli) {
  Write-Host ""
  Write-Host "▼ デスクトップアプリでプラグインを登録する手順（CLI不要・これを行わないと skill が使えません）:" -ForegroundColor Cyan
  Write-Host "  1. アプリのプロンプト横の [＋] → Plugins（または chat に /plugin と入力）"
  Write-Host "  2. Marketplaces タブ → Add marketplace → 次を貼付:"
  Write-Host "       $Marketplace"
  Write-Host "     （GitHub から入れる場合は https://github.com/yuu-sysp/llm-wiki-marketplace.git）"
  Write-Host "  3. Discover タブ → llm-wiki を選び Install → スコープ User"
  Write-Host ("     → vault_root に `"{0}`" を入力して Confirm" -f $VaultRoot)
  Write-Host "  4. /reload-plugins でリロード（/llm-wiki:init 等が出れば成功）"
  Write-Host ""
  Write-Host "  ※ 3. の vault_root を空のまま Confirm しないこと。" -ForegroundColor Yellow
  Write-Host "     空のままだと skill が vault を解決できず"
  Write-Host "     「Vault が未設定で inbox の場所が解決できない」というエラーになります。" -ForegroundColor Yellow
  Write-Host ""
  Write-Host "  CLI も入れたい場合（依存なし・自動更新・管理者権限不要）:"
  Write-Host "     irm https://claude.ai/install.ps1 | iex"
}
