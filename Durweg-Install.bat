@echo off
rem Durweg-Install.bat: double-click on Windows to install Durweg, on Windows itself or inside WSL.
rem The PowerShell part below the marker does the work; a durweg-rc.json next to this file names a
rem release candidate instead of the published version (testing before a release).
setlocal
set "DURWEG_SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:DURWEG_SELF,[Text.Encoding]::UTF8); $m='#=== '+'ps1 ==='; Invoke-Expression $s.Substring($s.IndexOf($m))"
set "RC=%ERRORLEVEL%"
echo.
if not defined DURWEG_NO_PAUSE pause
exit /b %RC%

#=== ps1 ===
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Version = 'v1.0.0'
$Repo = 'musetee/durweg'
$Here = Split-Path -Parent $env:DURWEG_SELF
$Local = Join-Path $env:LOCALAPPDATA 'Durweg'
$DHome = if ($env:DURWEG_HOME) { $env:DURWEG_HOME } else { Join-Path $HOME 'Durweg' }
$Utf8 = New-Object System.Text.UTF8Encoding $false
New-Item -ItemType Directory -Force -Path $Local | Out-Null

function Read-Json($p) { if (Test-Path $p) { try { return [IO.File]::ReadAllText($p) | ConvertFrom-Json } catch { } }; return $null }
function Write-Json($p, $o) { [IO.File]::WriteAllText($p, ($o | ConvertTo-Json -Depth 5), $Utf8) }

# ---- remembered choices (a second double-click after a restart goes on without asking) ---------
$SetupFile = Join-Path $Local 'setup.json'
$setup = Read-Json $SetupFile
$Lang = $env:DURWEG_LANG
if (-not $Lang -and $setup) { $Lang = $setup.language }
if (-not $Lang) {
    Write-Host ''; Write-Host '  Durweg'; Write-Host ''; Write-Host '  1) English'; Write-Host '  2) 中文'; Write-Host ''
    $a = Read-Host '  Language / 语言 [1]'
    $Lang = if ($a -like '2*') { 'zh' } else { 'en' }
}
function T($en, $zh) { if ($Lang -eq 'zh') { $zh } else { $en } }
function Say($en, $zh) { Write-Host ('  ' + (T $en $zh)) }
function Ok($en, $zh) { Write-Host ('  [OK] ' + (T $en $zh)) }
function Stop-Install($en, $zh) {
    Write-Host ('  [X]  ' + (T $en $zh))
    Write-Host ('       ' + (T 'Fix this, then double-click Durweg-Install.bat again.' '解决以后，再双击一次 Durweg-Install.bat。'))
    exit 1
}

$Target = $env:DURWEG_TARGET
if (-not $Target -and $setup) { $Target = $setup.target }
if (-not $Target) {
    Write-Host ''
    Say 'Where should Durweg be installed?' 'Durweg 装在哪里？'
    Say '  1) Windows (for workflows that run on Windows)' '  1) Windows（用于支持 Windows 的工作流）'
    Say '  2) WSL, Linux inside Windows (also for workflows that need Linux)' '  2) WSL，Windows 里的 Linux（也能跑需要 Linux 的工作流）'
    $a = Read-Host ('  ' + (T 'Choice [1]' '选择 [1]'))
    $Target = if ($a -like '2*') { 'wsl' } else { 'windows' }
}
Write-Json $SetupFile @{ language = $Lang; target = $Target }

# ---- release candidate next to this file, if any ---------------------------------------------
$rc = Read-Json (Join-Path $Here 'durweg-rc.json')
if ($rc) { $Version = $rc.version }
if ($env:DURWEG_VERSION) { $Version = $env:DURWEG_VERSION }

# ==== WSL =======================================================================================
if ($Target -eq 'wsl') {
    & wsl.exe -e true 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Say 'WSL is installed now; Windows asks for administrator approval.' '现在安装 WSL；Windows 会请求管理员授权。'
        Say 'When it has finished: restart the computer, open "Ubuntu" from the Start menu once to choose a' '装完以后：重启电脑，从开始菜单打开一次 "Ubuntu"，设置 Linux 用户名和密码，'
        Say 'Linux user name and password, then double-click Durweg-Install.bat again.' '然后再双击一次 Durweg-Install.bat。'
        Start-Process wsl.exe -ArgumentList '--install', '-d', 'Ubuntu' -Verb RunAs -Wait
        exit 0
    }
    if ($rc) {
        $tar = (& wsl.exe wslpath -u ((Join-Path $Here $rc.tar) -replace '\\', '/')).Trim()
        $cmd = "export DURWEG_LANG=$Lang DURWEG_VERSION=$Version DURWEG_SOURCE='$tar' DURWEG_SHA256=$($rc.tar_sha256); " +
               "s=`$(mktemp); tar -xzOf `"`$DURWEG_SOURCE`" durweg-$Version/install.sh > `"`$s`" && bash `"`$s`""
    } else {
        $cmd = "export DURWEG_LANG=$Lang DURWEG_VERSION=$Version; cd ~ && " +
               "curl -fsSL https://raw.githubusercontent.com/$Repo/$Version/install.sh -o /tmp/durweg-install.sh && bash /tmp/durweg-install.sh"
    }
    if ($env:DURWEG_NO_START) { $cmd = "export DURWEG_NO_START=1; $cmd" }
    & wsl.exe -e bash -lc $cmd
    exit $LASTEXITCODE
}

# ==== Windows ===================================================================================
Write-Host ''
Say "Installing Durweg $Version on Windows" "正在把 Durweg $Version 装到 Windows 上"

# ---- Python 3.10 or newer --------------------------------------------------------------------
function Find-Python {
    foreach ($c in @(@('py', '-3'), @('python'))) {
        if (Get-Command $c[0] -ErrorAction SilentlyContinue) {
            $args2 = @($c | Select-Object -Skip 1) + @('-c', 'import sys; sys.exit(sys.version_info < (3, 10))')
            & $c[0] @args2 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return , $c }
        }
    }
    return $null
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
$Py = Find-Python
if (-not $Py) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Stop-Install 'Python 3 is missing and winget is not available. Install Python from python.org.' '缺少 Python 3，而且没有 winget。请从 python.org 安装 Python。'
    }
    Say 'Installing Python 3.12 (winget)...' '正在安装 Python 3.12（winget）……'
    & winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements | Out-Host
    Refresh-Path
    $Py = Find-Python
    if (-not $Py) { Stop-Install 'Python was installed but cannot be found yet.' 'Python 已经装好，但现在还找不到。' }
}
$PyExe = $Py[0]; $PyArgs = @($Py | Select-Object -Skip 1)
Ok 'Python' 'Python'

# ---- the fixed version, checked by sha256, tried before it becomes current --------------------
$Pkg = Join-Path $Local "durweg-$Version.zip"
if ($env:DURWEG_SOURCE) { $Src = $env:DURWEG_SOURCE; $Sha = $env:DURWEG_SHA256 }
elseif ($rc) { $Src = Join-Path $Here $rc.zip; $Sha = $rc.zip_sha256 }
else { $Src = "https://github.com/$Repo/releases/download/$Version/durweg-$Version.zip"; $Sha = $null }
try {
    if ($Src -match '^https?://') {
        Invoke-WebRequest -UseBasicParsing -Uri $Src -OutFile $Pkg
        if (-not $Sha) { $Sha = ((Invoke-WebRequest -UseBasicParsing -Uri "$Src.sha256").Content -split '\s+')[0] }
    } else { Copy-Item -LiteralPath $Src -Destination $Pkg -Force }
} catch { Stop-Install "Download failed: $Src" "下载失败：$Src" }
if (-not $Sha) { Stop-Install 'No sha256 for the download, so it cannot be checked.' '下载没有附带 sha256，无法校验。' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Pkg).Hash.ToLower() -ne $Sha.ToLower()) {
    Stop-Install 'The download is damaged (sha256 differs); try again.' '下载的文件不完整（sha256 不符），请重试。'
}
$New = Join-Path $Local $Version
if (-not (Test-Path (Join-Path $New 'bin\durweg'))) {
    $Tmp = Join-Path $Local ".unpack-$Version"
    if (Test-Path $Tmp) { Remove-Item -Recurse -Force $Tmp }
    Expand-Archive -LiteralPath $Pkg -DestinationPath $Tmp
    $Top = Join-Path $Tmp "durweg-$Version"
    & $PyExe @PyArgs (Join-Path $Top 'bin\durweg') --version | Out-Null
    if ($LASTEXITCODE -ne 0) { Stop-Install 'This Durweg version does not run here.' '这个版本的 Durweg 在这里运行不了。' }
    if (Test-Path $New) { Remove-Item -Recurse -Force $New }
    Move-Item $Top $New
    Remove-Item -Recurse -Force $Tmp
}
Remove-Item -Force $Pkg -ErrorAction SilentlyContinue

# ---- the durweg command ----------------------------------------------------------------------
$BinDir = Join-Path $Local 'bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$Launcher = Join-Path $BinDir 'durweg.cmd'
$pyLine = ($PyExe + ' ' + ($PyArgs -join ' ')).Trim()
[IO.File]::WriteAllText($Launcher, "@echo off`r`nrem durweg launcher (written by Durweg-Install.bat)`r`n$pyLine `"$New\bin\durweg`" %*`r`n", $Utf8)
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$pathEntries = @()
if (-not (($userPath -split ';') -contains $BinDir)) {
    [Environment]::SetEnvironmentVariable('Path', (($userPath.TrimEnd(';') + ';' + $BinDir).TrimStart(';')), 'User')
    $pathEntries = @($BinDir)
}
$env:Path = "$BinDir;$env:Path"
& $Launcher --version | Out-Null
if ($LASTEXITCODE -ne 0) { Stop-Install 'The durweg command does not run.' 'durweg 命令运行不了。' }
Ok "Durweg $Version, command: durweg" "Durweg $Version，命令：durweg"

# ---- ~/Durweg: settings and the library with the example --------------------------------------
New-Item -ItemType Directory -Force -Path (Join-Path $DHome 'workflows') | Out-Null
$cfgPath = Join-Path $DHome 'config.json'
$cfg = Read-Json $cfgPath
if (-not $cfg) { $cfg = [pscustomobject]@{} }
$cfg | Add-Member -NotePropertyName language -NotePropertyValue $Lang -Force
Write-Json $cfgPath $cfg
$lib = Read-Json (Join-Path $DHome 'library.json')
$ex = if ($lib -and $lib.workflows) { $lib.workflows.'write-your-method' } else { $null }
if ($ex -and $ex.path -like "$Local*") { & $Launcher library remove write-your-method | Out-Null; $ex = $null }
if (-not $ex) {
    & $Launcher library add (Join-Path $New 'examples\write-your-method') --name write-your-method | Out-Null
    if ($LASTEXITCODE -ne 0) { Stop-Install 'The example could not be added to the library.' '示例无法加入方法库。' }
}
Ok "Your folder: $DHome" "你的文件夹：$DHome"

# ---- agents and their skills (copies, marked as Durweg's) -------------------------------------
$agents = @()
if ((Get-Command claude -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $HOME '.claude'))) { $agents += 'claude' }
if ((Get-Command codex -ErrorAction SilentlyContinue) -or (Test-Path (Join-Path $HOME '.codex'))) { $agents += 'codex' }
if ($agents.Count -eq 0) {
    $choice = $env:DURWEG_AGENT
    if (-not $choice) {
        Say 'No AI agent found. Which one should be installed?' '没有找到 AI agent。要装哪一个？'
        Write-Host '  1) Claude Code'; Write-Host '  2) Codex'
        $a = Read-Host '  [1]'
        $choice = if ($a -like '2*') { 'codex' } else { 'claude' }
    }
    try {
        if ($choice -eq 'claude') { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression; Refresh-Path; $env:Path = "$BinDir;$env:Path" }
        elseif ($choice -eq 'codex') {
            if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
                & winget install -e --id OpenJS.NodeJS.LTS --scope user --accept-package-agreements --accept-source-agreements | Out-Host
                Refresh-Path; $env:Path = "$BinDir;$env:Path"
            }
            & npm install -g @openai/codex | Out-Host
        }
    } catch { Stop-Install "Installing $choice failed." "安装 $choice 失败。" }
    if ($choice -ne 'skip') { $agents += $choice }
}
$skills = @()
foreach ($a in $agents) {
    $dir = if ($a -eq 'claude') { Join-Path $HOME '.claude\skills' } else { Join-Path $HOME '.codex\skills' }
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    foreach ($s in @('run-workflow', 'write-your-method')) {
        $src = Join-Path $New "skills\$s"
        if (-not (Test-Path $src)) { $src = Join-Path $New "examples\$s\skills\$s" }
        $dst = Join-Path $dir $s
        if ((Test-Path $dst) -and -not (Test-Path (Join-Path $dst '.durweg-owned'))) {
            Say "Kept $dst`: it is not Durweg's." "保留了 $dst：它不属于 Durweg。"; continue
        }
        if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
        Copy-Item -Recurse $src $dst
        [IO.File]::WriteAllText((Join-Path $dst '.durweg-owned'), "copied by Durweg $Version`r`n", $Utf8)
        $skills += $dst
    }
}
if ($agents.Count -gt 0) { Ok ('Skills for: ' + ($agents -join ', ')) ('已为这些 agent 装好 skill：' + ($agents -join '、')) }

# ---- install manifest (durweg uninstall reads it) ---------------------------------------------
$old = Read-Json (Join-Path $DHome '.install.json')
if ($old -and $old.path_entries) { $pathEntries = @($old.path_entries) + $pathEntries | Select-Object -Unique }
Write-Json (Join-Path $DHome '.install.json') ([ordered]@{
    format = 1; version = $Version; sha256 = $Sha.ToLower(); platform_dir = $New; data_dir = $Local
    launchers = @($Launcher); skills = @($skills); path_lines = @(); path_entries = @($pathEntries) })

# ---- start ------------------------------------------------------------------------------------
$first = T 'Please talk to me in English. Use durweg to run the example write-your-method with me (skill run-workflow).' '请用中文和我交流。用 durweg 带我运行示例 write-your-method（skill run-workflow）。'
Write-Host ''
Say 'Durweg is installed.' 'Durweg 装好了。'
if ($agents.Count -gt 0 -and -not $env:DURWEG_NO_START -and (Get-Command $agents[0] -ErrorAction SilentlyContinue)) {
    Say "Starting $($agents[0]) with the first example (it may ask you to log in first)..." "正在启动 $($agents[0])，带你做第一个示例（第一次可能会先让你登录）……"
    Set-Location $HOME
    & $agents[0] $first
    exit 0
}
Say 'Next: open a new terminal, start your agent, and tell it:' '下一步：打开一个新终端，启动你的 agent，然后对它说：'
Write-Host "    $first"
exit 0
