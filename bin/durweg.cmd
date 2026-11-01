@echo off
rem durweg.cmd: the Durweg command on Windows for the Claude Code plugin (PowerShell, cmd). The
rem installer writes its own durweg.cmd. Runs bin\durweg with the first Python 3.9 or newer, like
rem the sh part of bin\durweg.
setlocal
set "DURWEG_PY="
call py -3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "DURWEG_PY=py -3"
if not defined DURWEG_PY call python -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "DURWEG_PY=python"
if not defined DURWEG_PY call python3 -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>nul && set "DURWEG_PY=python3"
if not defined DURWEG_PY (
    echo durweg: needs Python 3.9 or newer ^(python3, python or py -3^); none was found 1>&2
    exit /b 3
)
rem no CALL here: CALL would expand %% in the arguments a second time; when DURWEG_PY is itself a
rem .cmd, control passes to it for good, which is fine as this is the last step
%DURWEG_PY% "%~dp0durweg" %*
exit /b %errorlevel%
