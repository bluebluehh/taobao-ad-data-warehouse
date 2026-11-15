@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
echo Publishing reviewed project files to bluebluehh/taobao-ad-data-warehouse
echo Raw data, databases, temporary files and third-party course materials are excluded.
git --version >nul 2>&1
if errorlevel 1 goto :no_git
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 goto :failed
for /f "delims=" %%B in ('git branch --show-current') do set "project_branch=%%B"
if not "%project_branch%"=="main" goto :wrong_branch
for /f "delims=" %%R in ('git remote get-url origin') do set "project_remote=%%R"
if not "%project_remote%"=="https://github.com/bluebluehh/taobao-ad-data-warehouse.git" goto :wrong_remote
python -m warehouse.static_check
if errorlevel 1 goto :failed
where node >nul 2>&1
if errorlevel 1 goto :stage
node tests/dashboard_checks.cjs
if errorlevel 1 goto :failed
:stage
git add .gitignore .gitattributes README.md docs warehouse sql web scripts tests examples
if errorlevel 1 goto :failed
git diff --cached --check
if errorlevel 1 goto :failed
echo.
git --no-pager diff --cached --stat
echo.
git diff --cached --quiet
if not errorlevel 1 goto :push
git -c user.name=bluebluehh -c user.email=219071822+bluebluehh@users.noreply.github.com commit -m "feat: publish reproducible Taobao ad warehouse and visual dashboard"
if errorlevel 1 goto :failed
:push
echo Uploading commit to GitHub. If sign-in opens, complete the normal GitHub login.
echo Network stalls will stop after about 45 seconds of very low transfer speed.
python scripts/push_github.py
if errorlevel 1 goto :failed
echo.
echo SUCCESS: https://github.com/bluebluehh/taobao-ad-data-warehouse
pause
exit /b 0
:no_git
echo Git is not available in PATH. Install Git for Windows or open this project in Git Bash.
goto :finish_error
:wrong_branch
echo Stopped: expected branch main. No branch was renamed or overwritten.
goto :finish_error
:wrong_remote
echo Stopped: origin does not match the intended GitHub repository.
goto :finish_error
:failed
echo.
echo Publishing did not finish. Review the error above. Existing remote history was not overwritten.
echo If GitHub asks for sign-in, use the normal browser sign-in. Do not paste tokens into project files.
:finish_error
pause
exit /b 1
