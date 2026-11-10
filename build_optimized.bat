@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Usage:
REM   build_optimized.bat              → profile from PAPERFLICK_BUILD_PROFILE or patch
REM   build_optimized.bat patch|minor|major
REM
REM Profiles (semver bump → compile cost):
REM   patch  — LTO off, keep Nuitka/clcache, do not wipe dist first (fast iteration)
REM   minor  — LTO off, keep caches, wipe dist then full folder rebuild
REM   major  — LTO on, keep caches, wipe dist (shipping-quality link)

echo ========================================
echo PaperFlick Nuitka standalone build
echo ========================================

set APP_NAME=PaperFlick
set MAIN_FILE=PaperFlick.py
set ICON_FILE=icons\PaperFlick.ico

set PROFILE=%~1
if "%PROFILE%"=="" set PROFILE=%PAPERFLICK_BUILD_PROFILE%
if "%PROFILE%"=="" set PROFILE=patch

if /I not "%PROFILE%"=="patch" if /I not "%PROFILE%"=="minor" if /I not "%PROFILE%"=="major" (
    echo [error] unknown profile "%PROFILE%" — use patch, minor, or major
    exit /b 2
)

set LTO_MODE=no
set CLEAN_DIST=0
if /I "%PROFILE%"=="minor" set CLEAN_DIST=1
if /I "%PROFILE%"=="major" (
    set LTO_MODE=yes
    set CLEAN_DIST=1
)

set CPU_CORES=%NUMBER_OF_PROCESSORS%
if not defined CPU_CORES set CPU_CORES=4
set /a BUILD_JOBS=%CPU_CORES%

set EXCLUDE_MODULES=unittest,test,pytest,_pytest,doctest,pdb,pdbpp
set EXCLUDE_MODULES=%EXCLUDE_MODULES%,setuptools,pip,distutils,pkg_resources
set EXCLUDE_MODULES=%EXCLUDE_MODULES%,email.mime,http.server,xmlrpc,pydoc

echo.
echo profile=%PROFILE%  lto=%LTO_MODE%  clean_dist=%CLEAN_DIST%  jobs=%BUILD_JOBS%
echo caches: Nuitka/clcache under %%LOCALAPPDATA%% are kept for all profiles
echo.

echo [1/4] Prepare dist...
if "%CLEAN_DIST%"=="1" (
    if exist dist rd /s /q dist
    echo - wiped dist\ for full folder rebuild
) else (
    echo - keeping dist\ if present ^(patch / incremental^)
)

echo.
echo [2/4] Nuitka compile...
call "%ProgramFiles%\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
mamba run -n paperflick python -m nuitka --standalone ^
    --windows-console-mode=disable ^
    --lto=%LTO_MODE% ^
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
echo profile=%PROFILE% lto=%LTO_MODE%
exit /b 0
