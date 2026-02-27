@echo off
:: OctalFont Build CLI - Windows launcher
:: Requires Git Bash / MSYS2 / Cygwin on PATH (provides bash).
::
:: Usage: octalfont.bat <command> [options]
::   (same interface as the bash script; run `octalfont help` for details)

where bash >nul 2>&1
if errorlevel 1 (
    echo [ERROR] bash not found on PATH.
    echo         Install Git for Windows ^(https://git-scm.com/download/win^) and
    echo         ensure '%PROGRAMFILES%\Git\bin' is on your PATH.
    exit /b 1
)

bash "%~dp0octalfont" %*
