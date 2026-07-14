[app]
title = 视频提取器
p4a.url = https://gitee.com/mirrors/python-for-android.git
p4a.fork = mirrors
package.name = videoextractor
package.domain = org.videoextractor
source.dir = ..
source.include_exts = py,png,jpg,kv,atlas,ttf
source.include_patterns = video_downloader/*.py
version = 1.0.0
requirements = python3,kivy==2.3.1,yt-dlp,requests
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[android]
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 34
android.gradle_deps = androidx.core:core:1.9.0
android.arch = arm64-v8a
android.allow_backup = True
android.presplash_color = #1e1e2e
android.splash_color = #1e1e2e
p4a.branch = develop
p4a.bootstrap = sdl2

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,FOREGROUND_SERVICE,POST_NOTIFICATIONS

android.features = android.hardware.screen.PORTRAIT

android.add_java_activity =
android.add_jar =
android.add_aars =
android.add_src =

android.release_artifact = aab
android.sign = 0
android.package_signing = 0

p4a.local_recipes =
p4a.whitelist =
p4a.blacklist =
p4a.hook =
p4a.create_bootstrap = yes
