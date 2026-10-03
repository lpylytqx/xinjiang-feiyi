@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 新疆非遗平台 - 一键更新到 GitHub

rem ============================================================
rem  一键更新到 GitHub
rem
rem  用法：双击本文件即可。
rem  脚本用 %~dp0 自动定位到自身所在目录，
rem  因此项目文件夹改名、换盘符都不受影响。
rem
rem  与旧版的区别：
rem    1. 不再硬编码 D:\xinjiang_feiyi
rem    2. 提交前检查 config_local.py / .env 是否混入（防止 API Key 泄露）
rem    3. 每一步都检查执行结果，失败会明确报错并停下
rem    4. 推送前显示将要提交的文件清单，可确认后再继续
rem ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   新疆非遗文化互动体验平台 - 更新到 GitHub
echo ============================================================
echo.

rem ---------- 1/6 检查 Git ----------
echo [1/6] 检查 Git 环境...
where git >nul 2>nul
if errorlevel 1 (
    echo.
    echo   [错误] 没有找到 git 命令。
    echo   请先安装 Git for Windows：https://git-scm.com/download/win
    echo   安装完成后，重新打开命令行窗口再运行本脚本。
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('git --version') do echo        %%v

rem ---------- 2/6 检查仓库 ----------
echo.
echo [2/6] 检查仓库状态...
if not exist ".git" (
    echo.
    echo   [错误] 当前目录不是 Git 仓库。
    echo   当前目录：%CD%
    echo.
    pause
    exit /b 1
)
set "BRANCH="
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%b"
if not defined BRANCH set "BRANCH=main"
echo        当前目录：%CD%
echo        当前分支：%BRANCH%

rem ---------- 3/6 暂存 + 敏感文件检查 ----------
echo.
echo [3/6] 暂存改动并检查敏感文件...
git add -A >nul 2>nul

set "STAGED=%TEMP%\_xj_staged.txt"
git diff --cached --name-only >"%STAGED%" 2>nul

findstr /i /c:"config_local.py" /c:".env" "%STAGED%" >nul 2>nul
if not errorlevel 1 (
    echo.
    echo   [危险] 待提交文件里出现了 config_local.py 或 .env！
    echo.
    echo   这两个文件含有 API Key，一旦推送就会在 GitHub 上公开泄露。
    echo   请先确认 .gitignore 中包含 config_local.py 这一行，然后重新运行。
    echo.
    echo   已自动取消本次暂存，不会误提交。
    git reset >nul 2>nul
    del "%STAGED%" >nul 2>nul
    pause
    exit /b 1
)
echo        敏感文件检查通过。

rem ---------- 4/6 显示改动 ----------
echo.
echo [4/6] 本次将要提交的改动：
echo ------------------------------------------------------------
type "%STAGED%"
echo ------------------------------------------------------------

set "COUNT=0"
for /f %%c in ('find /c /v "" ^< "%STAGED%"') do set "COUNT=%%c"
del "%STAGED%" >nul 2>nul
echo        共 !COUNT! 个文件。

if "!COUNT!"=="0" (
    echo.
    echo        没有需要提交的改动，仓库已是最新状态。
    echo.
    pause
    exit /b 0
)

echo.
set "MSG="
set /p "MSG=请输入本次更新的说明（直接回车使用默认）："
if not defined MSG set "MSG=更新：%date% %time%"

rem ---------- 5/6 提交 ----------
echo.
echo [5/6] 提交到本地仓库...
git commit -m "!MSG!"
if errorlevel 1 (
    echo.
    echo   [错误] 提交失败，请查看上面的提示信息。
    echo.
    pause
    exit /b 1
)

rem ---------- 6/6 推送 ----------
echo.
echo [6/6] 推送到远程仓库...

set "REMOTES=%TEMP%\_xj_remotes.txt"
git remote >"%REMOTES%" 2>nul

findstr /x /c:"origin" "%REMOTES%" >nul 2>nul
if errorlevel 1 (
    echo        [跳过] 没有配置名为 origin 的远程仓库。
    echo        可用这条命令添加：
    echo        git remote add origin https://github.com/用户名/仓库名.git
) else (
    echo        正在推送到 origin / %BRANCH% ...
    git push origin %BRANCH%
    if errorlevel 1 (
        echo.
        echo   [错误] 推送失败，常见原因：
        echo          1. 未登录 GitHub —— 首次推送会弹出登录窗口，完成登录后重新运行本脚本
        echo          2. 网络不通 —— 国内访问 GitHub 有时需要代理
        echo          3. 远程有新提交 —— 先执行 git pull 再重试
        echo.
        echo   本地提交已经成功，修好问题后重新运行本脚本只会补做推送。
        del "%REMOTES%" >nul 2>nul
        pause
        exit /b 1
    )
)

rem 可选：如果还配置了 Gitee 远程，一并推送
findstr /x /c:"gitee" "%REMOTES%" >nul 2>nul
if not errorlevel 1 (
    echo        检测到 gitee 远程，一并推送...
    git push gitee %BRANCH%
    if errorlevel 1 echo        [提示] gitee 推送失败，但 GitHub 已更新成功。
)
del "%REMOTES%" >nul 2>nul

echo.
echo ============================================================
echo   完成！代码已更新到 GitHub
echo ============================================================
echo.
pause
exit /b 0
