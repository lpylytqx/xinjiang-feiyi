@echo off
chcp 936 >nul
title 新疆非遗文化互动体验平台 - 启动中
cd /d "%~dp0"
setlocal

echo ============================================================
echo   基于 AIGC 的新疆非遗文化互动体验平台
echo ------------------------------------------------------------
echo   启动完成后浏览器访问：http://127.0.0.1:5000
echo   关闭本窗口或按 Ctrl+C 可停止服务
echo ============================================================
echo.

echo [1/4] 正在查找可用的 Python...
set "PYEXE="

rem 优先使用 py 启动器（最可靠，能自动找到真实的 Python）
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYEXE=py -3"
)

rem 退而求其次：python 命令，但必须验证它真的能运行（排除 Microsoft Store 别名）
if not defined PYEXE (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; print(sys.executable)" >nul 2>nul
        if not errorlevel 1 set "PYEXE=python"
    )
)

rem 最后尝试常见安装路径
if not defined PYEXE (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
    ) do (
        if not defined PYEXE if exist %%P set "PYEXE=%%~P"
    )
)

if not defined PYEXE (
    echo.
    echo [错误] 没有找到可用的 Python。
    echo.
    echo    请安装 Python 3.10 或更高版本：https://www.python.org/downloads/
    echo    安装时务必勾选 "Add Python to PATH"。
    echo    如果已安装仍报此错，请重启命令提示符后重试。
    echo.
    pause
    exit /b 1
)

echo       使用：%PYEXE%
echo.
echo [2/4] 检查 Python 版本...
%PYEXE% --version
if errorlevel 1 (
    echo.
    echo [错误] Python 无法正常运行。
    echo.
    pause
    exit /b 1
)

echo.
echo [3/4] 检查并安装依赖（Flask / requests / Pillow）...
%PYEXE% -c "import flask, requests, PIL" >nul 2>nul
if errorlevel 1 (
    echo       缺少依赖，正在安装，请稍候...
    %PYEXE% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败。
        echo.
        echo    可能原因：网络不通、或 pip 源不可用。
        echo    可手动执行：%PYEXE% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo       依赖安装完成。
) else (
    echo       依赖已就绪。
)

echo.
echo [4/4] 正在启动网站...
echo ------------------------------------------------------------
echo   提示：若页面中 AI 功能不可用，属正常现象（断网时自动降级为本地模式）
echo ------------------------------------------------------------
echo.
set PYTHONUTF8=1
set FLASK_DEBUG=0

rem 延迟 3 秒后打开浏览器，此时服务应已就绪
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://127.0.0.1:5000"

%PYEXE% app.py
echo.
echo 网站已停止运行。
pause
