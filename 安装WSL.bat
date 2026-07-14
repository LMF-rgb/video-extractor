@echo off
echo ============================================
echo   安装 WSL (Windows 子系统 Linux)
echo   用于构建 Android APK
echo ============================================
echo.
echo 需要管理员权限。如果弹出 UAC 窗口请点"是"。
echo.

:: 请求管理员权限
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo 正在请求管理员权限...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo [1/2] 安装 WSL + Ubuntu...
wsl --install

echo.
echo [2/2] 安装完成后请重启电脑
echo.
echo 重启后打开此脚本所在目录，运行:
echo   构建APK.bat
echo.
pause
