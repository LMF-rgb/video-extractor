@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════╗
echo ║    🎬 全平台视频提取器                    ║
echo ║    正在启动...                            ║
echo ╚══════════════════════════════════════════╝
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python！请先安装 Python 3.10+
    echo    下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查并安装依赖
python -c "import yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo 📦 正在安装 yt-dlp...
    pip install yt-dlp -q
)

:: 启动原生桌面版
echo 🚀 启动桌面版...
start python desktop\app_tk.py

pause
