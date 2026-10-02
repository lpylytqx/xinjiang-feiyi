@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   新疆非遗文化互动体验平台
echo   启动后请用浏览器打开 http://127.0.0.1:5000
echo   关闭窗口或按 Ctrl+C 即可停止服务
echo ============================================
echo.
python app.py
echo.
echo 服务已停止，按任意键关闭窗口。
pause >nul
