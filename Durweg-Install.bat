@echo off
rem Durweg-Install.bat: double-click on Windows to install Durweg, on Windows itself or inside WSL.
rem The PowerShell part below the marker does the work; a durweg-rc.json next to this file names a
rem release candidate instead of the published version (testing before a release).
setlocal
set "DURWEG_SELF=%~f0"
rem Windows PowerShell builds its own module path; one inherited from PowerShell 7 breaks it
set "PSModulePath="
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:DURWEG_SELF,[Text.Encoding]::UTF8); $m='#=== '+'ps1 ==='; Invoke-Expression $s.Substring($s.IndexOf($m))"
set "RC=%ERRORLEVEL%"
echo.
if not defined DURWEG_NO_PAUSE pause
exit /b %RC%

#=== ps1 ===
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$Version = 'v1.1.2'
$Repo = 'musetee/durweg'
$Here = Split-Path -Parent $env:DURWEG_SELF
$Local = Join-Path $env:LOCALAPPDATA 'Durweg'
$DHome = if ($env:DURWEG_HOME) { $env:DURWEG_HOME } else { Join-Path $HOME 'Durweg' }
$Utf8 = New-Object System.Text.UTF8Encoding $false
New-Item -ItemType Directory -Force -Path $Local | Out-Null

# a value as one bash word: inside single quotes, a ' becomes '\'' (V1-C-012)
function Q($s) { "'" + ([string]$s -replace "'", "'\''") + "'" }
if ($env:DURWEG_TEST_QUOTE) { Write-Host (Q $env:DURWEG_TEST_QUOTE); exit 0 }
# the first word of a .sha256 file; Windows PowerShell hands a downloaded .sha256 over as bytes,
# not text, so turn bytes into text first (v1.0.0 read "55" and refused every download)
function Read-Sha($content) {
    $t = if ($content -is [byte[]]) { [Text.Encoding]::UTF8.GetString($content) } else { [string]$content }
    $w = ($t.Trim() -split '\s+')[0]
    if ($w -match '^[0-9a-fA-F]{64}$') { return $w.ToLower() } else { return $null }
}
if ($env:DURWEG_TEST_SHA_URL) { Write-Host ('sha=' + (Read-Sha (Invoke-WebRequest -UseBasicParsing -Uri $env:DURWEG_TEST_SHA_URL).Content)); exit 0 }
function Read-Json($p) { if (Test-Path $p) { try { return [IO.File]::ReadAllText($p) | ConvertFrom-Json } catch { } }; return $null }
function Write-Json($p, $o) { [IO.File]::WriteAllText($p, ($o | ConvertTo-Json -Depth 5), $Utf8) }

# Is Durweg installed inside WSL? Any failure, a missing wsl.exe or a WSL that does not answer
# within the time limit counts as "not confirmed", so the rerun question still appears (V1-C-009).
function Test-WslDurweg {
    $exe = if ($env:DURWEG_TEST_WSL_EXE) { $env:DURWEG_TEST_WSL_EXE } else { 'wsl.exe' }
    $arg = if ($env:DURWEG_TEST_WSL_ARGS) { $env:DURWEG_TEST_WSL_ARGS } else { '-e sh -c "test -x ~/.local/bin/durweg"' }
    $ms = if ($env:DURWEG_TEST_WSL_TIMEOUT_MS) { [int]$env:DURWEG_TEST_WSL_TIMEOUT_MS } else { 15000 }
    $p = $null
    try {
        $si = New-Object System.Diagnostics.ProcessStartInfo $exe, $arg
        $si.UseShellExecute = $false; $si.CreateNoWindow = $true
        $si.RedirectStandardOutput = $true; $si.RedirectStandardError = $true
        $p = [Diagnostics.Process]::Start($si)
        if (-not $p.WaitForExit($ms)) { try { $p.Kill() } catch { }; return $false }
        return ($p.ExitCode -eq 0)
    } catch { return $false } finally { if ($p) { $p.Dispose() } }
}
if ($env:DURWEG_TEST_PROBE) { Write-Host "probe installed=$(Test-WslDurweg)"; exit 0 }

# ---- remembered choices (a second double-click after a restart goes on without asking) ---------
$SetupFile = Join-Path $Local 'setup.json'
$setup = Read-Json $SetupFile
$Lang = $env:DURWEG_LANG
# update mode (durweg update, plan v1.1 U1): the last choices, no questions, nothing new for agents,
# no browser, no agent start, and the library is left to durweg update
if ($env:DURWEG_UPDATE) {
    $env:DURWEG_AGENT = 'skip'; $env:DURWEG_NO_START = '1'
    if (-not $Lang -and $setup) { $Lang = $setup.language }
    if (-not $env:DURWEG_TARGET -and $setup) { $env:DURWEG_TARGET = $setup.target }
}
if (-not $Lang -and $setup -and $setup.language -and -not $env:DURWEG_TARGET) {
    # a rerun: say what is there, ask whether to change it; Enter keeps (e.g. after the WSL restart)
    if ($setup.target -eq 'wsl') { $installed = Test-WslDurweg } else { $installed = Test-Path (Join-Path $Local 'bin\durweg.cmd') }
    $zhL = if ($setup.language -eq 'zh') { '中文' } else { '英文' }
    $enL = if ($setup.language -eq 'zh') { 'Chinese' } else { 'English' }
    $where = if ($setup.target -eq 'wsl') { 'WSL' } else { 'Windows' }
    Write-Host ''
    if ($installed) {
        Write-Host "  Durweg 已经装在这台电脑上（语言：$zhL，位置：$where）。"
        Write-Host '  要修改吗？'
        Write-Host '    回车   不修改，按上次的选择继续（更新或修复 Durweg）'
    } else {
        Write-Host "  上次的安装还没有完成（语言：$zhL，位置：$where）。"
        Write-Host '  要修改吗？'
        Write-Host '    回车   不修改，按上次的选择接着安装'
    }
    Write-Host '    c      重新选择语言和安装位置，重新安装 Durweg'
    Write-Host ''
    if ($installed) {
        Write-Host "  Durweg is already installed on this computer (language: $enL, in $where)."
        Write-Host '  Do you want to change it?'
        Write-Host '    Enter  no change: continue with the last choices (update or repair Durweg)'
    } else {
        Write-Host "  The last installation has not finished yet (language: $enL, in $where)."
        Write-Host '  Do you want to change it?'
        Write-Host '    Enter  no change: continue the installation with the last choices'
    }
    Write-Host '    c      choose the language and the place again, and install Durweg anew'
    Write-Host ''
    $a = Read-Host '  回车 / Enter，或 / or c'
    if ($a -like 'c*') { $setup = $null } else { $Lang = $setup.language }
} elseif (-not $Lang -and $setup) { $Lang = $setup.language }
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
        # -e runs wslpath directly, without a shell: a folder like "Durweg(1)" stays one path
        $tar = & wsl.exe -e wslpath -u ((Join-Path $Here $rc.tar) -replace '\\', '/')
        if ($LASTEXITCODE -ne 0 -or -not $tar) {
            Stop-Install "WSL cannot read the package next to this file: $Here" "WSL 读不到这个文件旁边的安装包：$Here"
        }
        $tar = ([string]$tar).Trim()
        $cmd = "export DURWEG_LANG=$Lang DURWEG_VERSION=$Version DURWEG_SOURCE=$(Q $tar) DURWEG_SHA256=$($rc.tar_sha256); " +
               "s=`$(mktemp); tar -xzOf `"`$DURWEG_SOURCE`" durweg-$Version/install.sh > `"`$s`" && bash `"`$s`""
    } else {
        $cmd = "export DURWEG_LANG=$Lang DURWEG_VERSION=$Version; cd ~ && " +
               "curl -fsSL https://raw.githubusercontent.com/$Repo/$Version/install.sh -o /tmp/durweg-install.sh && bash /tmp/durweg-install.sh"
    }
    if ($env:DURWEG_NO_START) { $cmd = "export DURWEG_NO_START=1; $cmd" }
    if ($env:DURWEG_NO_BROWSER) { $cmd = "export DURWEG_NO_BROWSER=1; $cmd" }
    $g = if ($env:DURWEG_GUIDE) { $env:DURWEG_GUIDE } elseif ($rc -and $rc.guide) { $rc.guide } else { $null }
    if ($g) { $cmd = "export DURWEG_GUIDE=$(Q $g); $cmd" }   # install.sh in WSL opens the guide
    & wsl.exe -e bash -lc $cmd
    exit $LASTEXITCODE
}

# ==== Windows ===================================================================================
Write-Host ''
Say "Installing Durweg $Version on Windows" "正在把 Durweg $Version 装到 Windows 上"

# ---- Python 3.10 or newer --------------------------------------------------------------------
function Find-Python {
    $own = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'   # a per-user python.org install
    foreach ($c in @(@('py', '-3'), @('python'), @($own))) {
        if ((Get-Command $c[0] -ErrorAction SilentlyContinue) -or (Test-Path $c[0])) {
            $args2 = @($c | Select-Object -Skip 1) + @('-c', 'import sys; sys.exit(sys.version_info < (3, 9))')
            & $c[0] @args2 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return , $c }
        }
    }
    return $null
}
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Install-PythonOrg {
    # Windows Sandbox, LTSC and older Windows 10 have no winget: the official installer from
    # python.org, accepted only with a valid signature of the Python Software Foundation.
    $pv = '3.12.10'
    $arch = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
    $url = "https://www.python.org/ftp/python/$pv/python-$pv-$arch.exe"
    $exe = Join-Path $Local "python-$pv-$arch.exe"
    Say "Downloading Python $pv from python.org..." "正在从 python.org 下载 Python $pv……"
    try { Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $exe } catch { Stop-Install "Download failed: $url" "下载失败：$url" }
    $sig = Get-AuthenticodeSignature -FilePath $exe
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notlike '*Python Software Foundation*') {
        Remove-Item -Force $exe
        Stop-Install 'The Python installer is not signed by the Python Software Foundation; it was not run.' 'Python 安装程序没有 Python Software Foundation 的有效签名，没有运行它。'
    }
    Say "Installing Python $pv (for this user)..." "正在安装 Python $pv（只装给当前用户）……"
    $p = Start-Process -FilePath $exe -ArgumentList '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1', 'Include_test=0' -Wait -PassThru
    Remove-Item -Force $exe -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0) { Stop-Install "The Python installer failed (exit $($p.ExitCode))." "Python 安装失败（退出码 $($p.ExitCode)）。" }
}
$Py = if ($env:DURWEG_TEST_PYTHON_DOWNLOAD) { $null } elseif ($env:DURWEG_TEST_PYTHON_EXE) { , @($env:DURWEG_TEST_PYTHON_EXE) } else { Find-Python }
if (-not $Py) {
    if ((Get-Command winget -ErrorAction SilentlyContinue) -and -not $env:DURWEG_TEST_PYTHON_DOWNLOAD) {
        Say 'Installing Python 3.12 (winget)...' '正在安装 Python 3.12（winget）……'
        & winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements | Out-Host
    } else {
        Install-PythonOrg
    }
    Refresh-Path
    $Py = if ($env:DURWEG_TEST_PYTHON_DOWNLOAD) { , @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe')) } else { Find-Python }
    $found = $false
    if ($Py) { $found = (Test-Path $Py[0]) -or [bool](Get-Command $Py[0] -ErrorAction SilentlyContinue) }
    if (-not $found) {
        Stop-Install 'Python was installed but cannot be found yet; double-click again.' 'Python 已经装好，但现在还找不到；请再双击一次。'
    }
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
        if (-not $Sha) { $Sha = Read-Sha (Invoke-WebRequest -UseBasicParsing -Uri "$Src.sha256").Content }
    } else { Copy-Item -LiteralPath $Src -Destination $Pkg -Force }
} catch { Stop-Install "Download failed: $Src" "下载失败：$Src" }
if (-not $Sha) { Stop-Install 'No sha256 for the download, so it cannot be checked.' '下载没有附带 sha256，无法校验。' }
function Get-Sha256($path) {   # .NET only: no PowerShell module needed
    $s = [IO.File]::OpenRead($path)
    try { return (([Security.Cryptography.SHA256]::Create().ComputeHash($s) | ForEach-Object { $_.ToString('x2') }) -join '') }
    finally { $s.Dispose() }
}
if ((Get-Sha256 $Pkg) -ne $Sha.ToLower()) {
    Stop-Install 'The download is damaged (sha256 differs); try again.' '下载的文件不完整（sha256 不符），请重试。'
}
$New = Join-Path $Local $Version
# always from the package just checked: a damaged copy of the same version is replaced (V1-C-003)
$Tmp = Join-Path $Local ".unpack-$Version"
if (Test-Path $Tmp) { Remove-Item -Recurse -Force $Tmp }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($Pkg, $Tmp)
$Top = Join-Path $Tmp "durweg-$Version"
& $PyExe @PyArgs (Join-Path $Top 'bin\durweg') --version | Out-Null
if ($LASTEXITCODE -ne 0) { Stop-Install 'This Durweg version does not run here.' '这个版本的 Durweg 在这里运行不了。' }
if (Test-Path $New) { if (Test-Path "$New.old") { Remove-Item -Recurse -Force "$New.old" }; Move-Item $New "$New.old" }
try {
    if ($env:DURWEG_TEST_FAIL_SWITCH) { throw 'switch failure injected for a test' }
    Move-Item $Top $New
} catch {
    # put the previous copy back so the existing durweg.cmd keeps working (V1-C-006)
    if ((Test-Path "$New.old") -and -not (Test-Path $New)) { Move-Item "$New.old" $New }
    Stop-Install "Could not put $New in place; the previous version is kept." "无法放置 $New；保留原来的版本。"
}
if (Test-Path "$New.old") { Remove-Item -Recurse -Force "$New.old" }
Remove-Item -Recurse -Force $Tmp
Remove-Item -Force $Pkg -ErrorAction SilentlyContinue

# ---- the durweg command ----------------------------------------------------------------------
$BinDir = Join-Path $Local 'bin'
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$Launcher = Join-Path $BinDir 'durweg.cmd'
$Mark = 'rem durweg launcher (written by Durweg-Install.bat)'
if ((Test-Path $Launcher) -and -not ([IO.File]::ReadAllText($Launcher) -like "*$Mark*")) {
    Stop-Install "$Launcher belongs to another program; it is left as it is." "$Launcher 属于别的程序，保持原样不动。"   # V1-C-005
}
$pyLine = ('"' + $PyExe + '" ' + ($PyArgs -join ' ')).Trim()     # quoted: a user name may hold spaces (V1-C-007)
# durweg.cmd never names a version: it runs bin\durweg-run.py, which reads bin\current.txt. So an
# update leaves durweg.cmd byte for byte as it was - durweg update runs inside it, and cmd.exe reads
# a batch file line by line while it runs, so a changed file could be read on from the wrong place
# (plan v1.1 U1)
$Runner = Join-Path $BinDir 'durweg-run.py'
$runPy = @'
"""durweg.cmd runs this; bin/current.txt names the installed version's folder (Durweg-Install.bat)."""
import os, runpy, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "current.txt"), encoding="utf-8-sig") as f:
    script = os.path.join(f.read().strip(), "bin", "durweg")
sys.argv[0] = script
runpy.run_path(script, run_name="__main__")
'@
[IO.File]::WriteAllText($Runner, ($runPy -replace "`r?`n", "`r`n"), $Utf8)
[IO.File]::WriteAllText((Join-Path $BinDir 'current.txt'), $New, $Utf8)
$launch = "@echo off`r`n$Mark`r`n$pyLine `"$Runner`" %*`r`n"
if (-not (Test-Path $Launcher) -or [IO.File]::ReadAllText($Launcher) -ne $launch) {
    [IO.File]::WriteAllText($Launcher, $launch, $Utf8)
}
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
# an agent counts when its command runs; a leftover settings folder alone does not (V1-C-004)
function Test-Agent($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { return $false }
    try { & $name --version 2>$null | Out-Null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}
$env:Path = "$env:Path;$(Join-Path $HOME '.local\bin')"
$agents = @()
# The agents Durweg supports and where each reads its skills. A new agent is one line in
# Get-SkillsDir, one Test-Agent line below, and a test.
function Get-SkillsDir($a) {
    switch ($a) {
        'claude' { Join-Path $HOME '.claude\skills' }
        'codex'  { Join-Path $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }) 'skills' }
        'agy'    { Join-Path $HOME '.gemini\config\skills' }        # Antigravity
    }
}
if (Test-Agent 'claude') { $agents += 'claude' }
if (Test-Agent 'codex') { $agents += 'codex' }
if (Test-Agent 'agy') { $agents += 'agy' }
if ($agents.Count -eq 0) {
    $choice = $env:DURWEG_AGENT
    if (-not $choice) {
        Say 'No AI agent found. Which one should be installed?' '没有找到 AI agent。要装哪一个？'
        Write-Host '  1) Claude Code'; Write-Host '  2) Codex'
        Write-Host ('  3) ' + (T 'I already have one and start it my own way (install nothing new)' '我已经装了，平时用自己的方式启动它（不装新的）'))
        $a = Read-Host '  [1]'
        $choice = if ($a -like '2*') { 'codex' } elseif ($a -like '3*') { 'own' } else { 'claude' }
    }
    # an agent started from its own place (not on PATH) still reads its skills from its settings
    # folder: give both agents the skills and let the user start theirs as usual
    if ($choice -eq 'own') { $agents = @('claude', 'codex'); $own = $true; $choice = 'skip' }
    try {
        if ($choice -eq 'claude') { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression; Refresh-Path; $env:Path = "$BinDir;$env:Path" }
        elseif ($choice -eq 'codex') {
            if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
                & winget install -e --id OpenJS.NodeJS.LTS --scope user --accept-package-agreements --accept-source-agreements | Out-Host
                Refresh-Path; $env:Path = "$BinDir;$env:Path"
            }
            & npm install -g @openai/codex | Out-Host
            if ($LASTEXITCODE -ne 0) { throw "npm exit $LASTEXITCODE" }
        }
    } catch { Stop-Install "Installing $choice failed." "安装 $choice 失败。" }
    if ($choice -ne 'skip' -and $choice -ne $null) {
        Refresh-Path; $env:Path = "$BinDir;$env:Path;$(Join-Path $HOME '.local\bin')"
        if (-not (Test-Agent $choice)) { Stop-Install "$choice was installed but does not run; open a new window and try again." "$choice 装好了但运行不了；请打开一个新窗口再试。" }
        $agents += $choice
    }
}
# Antigravity started from its own place: its settings or program folder is enough to give it the skills
$skillAgents = @($agents)
# an agent that already has Durweg's skills keeps getting them, even when it is not found now (it
# is started its own way, choice 3, or durweg update runs without asking): V11-C-009
foreach ($a in @('claude', 'codex', 'agy')) {
    if ($skillAgents -contains $a) { continue }
    foreach ($s in @('run-workflow', 'write-your-method')) {
        if (Test-Path (Join-Path (Join-Path (Get-SkillsDir $a) $s) '.durweg-owned')) { $skillAgents += $a; break }
    }
}
if ($skillAgents -notcontains 'agy' -and ((Test-Path (Join-Path $HOME '.gemini\antigravity-cli')) -or
        (Test-Path (Join-Path $env:LOCALAPPDATA 'agy\bin\agy.exe')))) { $skillAgents += 'agy' }
$skills = @()
foreach ($a in $skillAgents) {
    $dir = Get-SkillsDir $a
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
if ($skillAgents.Count -gt 0) { Ok ('Skills for: ' + ($skillAgents -join ', ')) ('已为这些 agent 装好 skill：' + ($skillAgents -join '、')) }

# ---- install manifest (durweg uninstall reads it) ---------------------------------------------
$old = Read-Json (Join-Path $DHome '.install.json')
if ($old -and $old.path_entries) { $pathEntries = @($old.path_entries) + $pathEntries | Select-Object -Unique }
# keep what an earlier run recorded and is still Durweg's, as install.sh does (V1-C-002, V11-C-009)
if ($old -and $old.skills) {
    $skills = @(@($old.skills) + $skills | Where-Object { $_ -and (Test-Path (Join-Path $_ '.durweg-owned')) } | Select-Object -Unique)
}
Write-Json (Join-Path $DHome '.install.json') ([ordered]@{
    format = 1; version = $Version; sha256 = $Sha.ToLower(); platform_dir = $New; data_dir = $Local
    launchers = @($Launcher); skills = @($skills); path_lines = @(); path_entries = @($pathEntries) })

# ---- your workflows from git, to their newest version (plan v1.1 C5) ---------------------------
# not in update mode: durweg update does this itself, with the new version, once
if (-not $env:DURWEG_UPDATE) {
    & $Launcher library update --quiet
    if ($LASTEXITCODE -ne 0) { Say 'Your workflows could not be updated now; durweg update tries again.' '你的工作流现在没能更新；durweg update 会再试一次。' }
}

# ---- the guide: the README on GitHub opens in the browser ---------------------------------------
$g = if ($env:DURWEG_GUIDE) { $env:DURWEG_GUIDE } elseif ($rc -and $rc.guide) { $rc.guide } else { "https://github.com/$Repo/blob/$Version/" }
$Guide = $g + (T 'README.md' 'README_cn.md')
Say "Guide: $Guide" "教程：$Guide"
if (-not $env:DURWEG_NO_START -and -not $env:DURWEG_NO_BROWSER) { try { Start-Process $Guide } catch { } }

# ---- start ------------------------------------------------------------------------------------
$first = T 'Please talk to me in English. Durweg has just been installed. First ask me whether to do the example write-your-method with me now (with skill run-workflow it turns one way I do my work into a workflow). If yes, start it; if not, tell me how to start it later.' '请用中文和我交流。Durweg 刚装好。先问我要不要现在一起做示例 write-your-method（用 skill run-workflow，把我的一个做事方法写成工作流）；要就开始，不要就告诉我以后怎么开始。'
Write-Host ''
Say 'Durweg is installed.' 'Durweg 装好了。'
if ($own) {
    Say 'Next: start your agent the way you always do, and tell it:' '下一步：照你平常的方式启动 agent，然后对它说：'
    Write-Host "    $first"
    exit 0
}
if ($agents.Count -gt 0 -and -not $env:DURWEG_NO_START -and (Get-Command $agents[0] -ErrorAction SilentlyContinue)) {
    Say "Starting $($agents[0]) with the first example (it may ask you to log in first)..." "正在启动 $($agents[0])，带你做第一个示例（第一次可能会先让你登录）……"
    Set-Location $HOME
    if ($agents[0] -eq 'agy') { & agy -i $first } else { & $agents[0] $first }   # Antigravity: prompt, then stay interactive
    exit 0
}
Say 'Next: open a new terminal, start your agent, and tell it:' '下一步：打开一个新终端，启动你的 agent，然后对它说：'
Write-Host "    $first"
exit 0
