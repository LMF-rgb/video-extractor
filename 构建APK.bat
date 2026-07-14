@echo off
chcp 65001 >nul
echo ============================================
echo   构建 Android APK
echo ============================================
echo.

:: 检查 WSL
wsl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ WSL 未安装！请先运行 安装WSL.bat
    pause
    exit /b 1
)

echo [1/4] 更新 WSL 软件包...
wsl bash -c "sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-dev build-essential libltdl-dev libffi-dev libssl-dev autoconf libtool cmake git openjdk-17-jdk zip unzip"

echo [2/4] 安装 Buildozer...
wsl bash -c "pip3 install cython buildozer"

echo [3/4] 构建 APK（首次约 20-30 分钟，请耐心等待）...
wsl bash -c "cd /mnt/c/Users/a/workspace/projects/003-video-extractor/android && buildozer android debug"

echo.
echo [4/4] 查找 APK...
dir /s /b android\bin\*.apk 2>nul
if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo   🎉 APK 构建成功！
    echo   📱 文件位置: android\bin\
    echo ============================================
    start android\bin
) else (
    echo ❌ 构建失败，请查看上方日志
)

pause
