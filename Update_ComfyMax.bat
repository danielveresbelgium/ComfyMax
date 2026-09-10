@echo off
setlocal EnableExtensions EnableDelayedExpansion

title ComfyMax Updater

cd /d "%~dp0"

echo.
echo ============================================================
echo                  ComfyMax Update Utility
echo ============================================================
echo.
echo Working folder:
echo %CD%
echo.

rem ------------------------------------------------------------
rem 1. Check Git
rem ------------------------------------------------------------

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git was not found.
    echo.
    echo Install Git for Windows first:
    echo https://git-scm.com/download/win
    echo.
    goto :failed
)

echo [OK] Git found.

rem ------------------------------------------------------------
rem 2. Check repository
rem ------------------------------------------------------------

if not exist ".git" (
    echo.
    echo [ERROR] This folder is not a Git repository.
    echo.
    echo Run this updater from the main ComfyMax folder.
    echo Expected location example:
    echo D:\ComfyMax-EN\Update_ComfyMax.bat
    echo.
    goto :failed
)

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Git cannot read this repository correctly.
    echo.
    goto :failed
)

echo [OK] ComfyMax Git repository detected.

rem ------------------------------------------------------------
rem 3. Determine current branch
rem ------------------------------------------------------------

for /f "delims=" %%B in ('git branch --show-current 2^>nul') do set "CURRENT_BRANCH=%%B"

if not defined CURRENT_BRANCH (
    echo.
    echo [ERROR] Could not determine the current Git branch.
    echo.
    goto :failed
)

echo [OK] Current branch: %CURRENT_BRANCH%

rem ------------------------------------------------------------
rem 4. Protect modified tracked files
rem ------------------------------------------------------------

set "TRACKED_CHANGES="

for /f "delims=" %%L in ('git status --porcelain --untracked-files^=no 2^>nul') do (
    set "TRACKED_CHANGES=1"
)

if defined TRACKED_CHANGES (
    echo.
    echo ============================================================
    echo UPDATE STOPPED - LOCAL CHANGES FOUND
    echo ============================================================
    echo.
    echo One or more existing ComfyMax files were modified locally.
    echo The updater will NOT overwrite or merge them automatically.
    echo.
    echo Modified tracked files:
    git status --short --untracked-files=no
    echo.
    echo Your own untracked workflows and files are allowed.
    echo Only changes to files already managed by Git block the update.
    echo.
    echo If these changes are intentional, commit them first.
    echo If they are not needed, restore them before updating.
    echo.
    goto :failed
)

echo [OK] No modified tracked ComfyMax files detected.

rem ------------------------------------------------------------
rem 5. Show untracked user files without blocking update
rem ------------------------------------------------------------

set "HAS_UNTRACKED="

for /f "delims=" %%L in ('git ls-files --others --exclude-standard 2^>nul') do (
    set "HAS_UNTRACKED=1"
)

if defined HAS_UNTRACKED (
    echo.
    echo [INFO] Untracked user files were detected.
    echo They will be left untouched.
    echo.
)

rem ------------------------------------------------------------
rem 6. Fetch latest version
rem ------------------------------------------------------------

echo.
echo Checking GitHub for updates...
echo.

git fetch origin
if errorlevel 1 (
    echo.
    echo [ERROR] Could not contact GitHub or fetch the repository.
    echo Check your internet connection and try again.
    echo.
    goto :failed
)

rem ------------------------------------------------------------
rem 7. Compare local and remote state
rem ------------------------------------------------------------

for /f "delims=" %%L in ('git rev-parse HEAD 2^>nul') do set "LOCAL_COMMIT=%%L"
for /f "delims=" %%R in ('git rev-parse origin/%CURRENT_BRANCH% 2^>nul') do set "REMOTE_COMMIT=%%R"

if not defined REMOTE_COMMIT (
    echo.
    echo [ERROR] Could not find origin/%CURRENT_BRANCH%.
    echo.
    goto :failed
)

if /I "%LOCAL_COMMIT%"=="%REMOTE_COMMIT%" (
    echo [INFO] ComfyMax source files are already up to date.
) else (
    echo [INFO] A newer version is available.
    echo.
    echo Updating ComfyMax...
    echo.

    git pull --rebase origin %CURRENT_BRANCH%
    if errorlevel 1 (
        echo.
        echo [ERROR] Git could not complete the update.
        echo.
        echo No automatic reset will be performed.
        echo Your files have not intentionally been deleted.
        echo.
        goto :failed
    )

    echo.
    echo [OK] ComfyMax source files updated successfully.
)

rem ------------------------------------------------------------
rem 8. Update Python packages
rem ------------------------------------------------------------

echo.
echo Checking Python environment...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [WARNING] ComfyMax .venv was not found.
    echo Python dependencies were not updated.
    echo.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    goto :success
)

echo [OK] ComfyMax Python environment found.

if not exist "requirements.txt" (
    echo [WARNING] requirements.txt was not found.
    echo Python dependencies were not updated.
    echo.
    goto :success
)

echo.
echo Updating required Python packages...
echo.

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [WARNING] ComfyMax files were updated, but one or more
    echo Python dependencies could not be installed.
    echo.
    echo Try running:
    echo .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    goto :partial
)

echo.
echo [OK] Python dependencies are up to date.

rem ------------------------------------------------------------
rem 9. Finish
rem ------------------------------------------------------------

:success
echo.
echo ============================================================
echo                    UPDATE COMPLETE
echo ============================================================
echo.
echo ComfyMax is ready.
echo You can now close this window and start ComfyMax normally.
echo.
pause
exit /b 0

:partial
echo.
echo ============================================================
echo                 UPDATE PARTIALLY COMPLETE
echo ============================================================
echo.
echo The ComfyMax source files were updated successfully,
echo but Python dependency installation reported a problem.
echo.
pause
exit /b 1

:failed
echo.
echo ============================================================
echo                     UPDATE NOT COMPLETED
echo ============================================================
echo.
echo Nothing was force-reset or intentionally overwritten.
echo Review the message above before trying again.
echo.
pause
exit /b 1
