@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo PaperFlick Nuitka standalone build
echo ========================================

set APP_NAME=PaperFlick
set MAIN_FILE=PaperFlick.py
set ICON_FILE=icons\PaperFlick.ico

set CPU_CORES=%NUMBER_OF_PROCESSORS%
if not defined CPU_CORES set CPU_CORES=4
set /a BUILD_JOBS=%CPU_CORES%

set EXCLUDE_MODULES=unittest,test,pytest,_pytest,doctest,pdb,pdbpp
set EXCLUDE_MODULES=%EXCLUDE_MODULES%,setuptools,pip,distutils,pkg_resources
set EXCLUDE_MODULES=%EXCLUDE_MODULES%,email.mime,http.server,xmlrpc,pydoc

echo.
echo [1/4] Clean old dist...
if exist dist rd /s /q dist

echo.
echo [2/4] Nuitka compile (jobs=%BUILD_JOBS%)...
call "%ProgramFiles%\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
mamba run -n paperflick python -m nuitka --standalone ^
    --windows-console-mode=disable ^
    --lto=yes ^
    --jobs=%BUILD_JOBS% ^
    --enable-plugin=anti-bloat ^
    --enable-plugin=tk-inter ^
    --noinclude-pytest-mode=nofollow ^
    --noinclude-setuptools-mode=nofollow ^
    --nofollow-import-to=%EXCLUDE_MODULES% ^
    --include-package=paperflick ^
    --include-package-data=paperflick ^
    --include-data-dir=src/paperflick/assets=paperflick/assets ^
    --include-package=customtkinter ^
    --include-package=tkinterdnd2 ^
    --include-package-data=customtkinter ^
    --include-package-data=tkinterdnd2 ^
    --python-flag=no_docstrings ^
    --output-dir=dist ^
    --output-filename=%APP_NAME%.exe ^
    --windows-icon-from-ico=%ICON_FILE% ^
    --assume-yes-for-downloads ^
    --remove-output ^
    %MAIN_FILE%

if %errorlevel% neq 0 (
    echo [error] Nuitka failed
    exit /b 1
)

echo.
echo [3/4] Measure dist size...
for /f %%a in ('powershell -NoProfile -Command "(Get-ChildItem -LiteralPath 'dist\%APP_NAME%.dist' -Recurse -File | Measure-Object -Property Length -Sum).Sum"') do set TOTAL_SIZE=%%a
set TOTAL_SIZE=%TOTAL_SIZE:,=%
set /a SIZE_MB=%TOTAL_SIZE% / 1048576
echo - dist size: %SIZE_MB% MB

echo.
echo [4/4] Slim dist...
powershell -ExecutionPolicy Bypass -File slim_dist.ps1 -DistPath "dist\%APP_NAME%.dist"

echo.
echo Build done: dist\%APP_NAME%.dist\%APP_NAME%.exe
exit /b 0
