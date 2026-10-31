@echo off
rem durweg.cmd: the Durweg command on Windows. Runs bin\durweg with Python (py launcher if present).
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0durweg" %*
) else (
    python "%~dp0durweg" %*
)
exit /b %errorlevel%
