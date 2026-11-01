@echo off
rem durweg.cmd: the Durweg command on Windows for the Claude Code plugin (PowerShell, cmd). The
rem installer writes its own durweg.cmd. Runs bin\durweg with the first Python 3.9 or newer, like
rem the sh part of bin\durweg (plan durweg-dev 20261101_durweg-plugin-windows.md, 2.1).
setlocal
set "DURWEG_PY="
call py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "DURWEG_PY=py -3"
if not defined DURWEG_PY call python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "DURWEG_PY=python"
if not defined DURWEG_PY call python3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "DURWEG_PY=python3"
if not defined DURWEG_PY (
    echo durweg: needs Python 3.9 or newer ^(python3, python or py -3^); none was found 1>&2
    exit /b 3
)
call %DURWEG_PY% "%~dp0durweg" %*
exit /b %errorlevel%
