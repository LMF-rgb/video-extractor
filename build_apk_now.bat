@echo off
chcp 65001 >nul
echo Starting APK build...
copy /Y "%~dp0android\build_apk.py" "%TEMP%\build_apk.py" >nul
wsl -d Ubuntu -u root -- cp "/mnt/$(echo %TEMP% | sed 's|\\|/|g' | sed 's|C:|c|')/build_apk.py" /root/video-extractor/android/build_apk.py
wsl -d Ubuntu -u root -- python3 /root/video-extractor/android/build_apk.py
pause
