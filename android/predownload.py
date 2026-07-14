#!/usr/bin/env python3
"""预下载 p4a 所有依赖到缓存，解决墙的问题"""

import os, re, sys, subprocess

RECIPES_DIR = "/root/video-extractor/android/.buildozer/android/platform/python-for-android/pythonforandroid/recipes"
PKG_CACHE = "/root/video-extractor/android/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/packages"
MIRROR = "https://ghproxy.net/"

os.makedirs(PKG_CACHE, exist_ok=True)

# Collect all recipes with their URLs and versions
recipes = []
for root, dirs, files in os.walk(RECIPES_DIR):
    for f in files:
        if f == "__init__.py":
            path = os.path.join(root, f)
            name = os.path.basename(os.path.dirname(path))
            with open(path, "r") as fp:
                content = fp.read()

            # Find version
            ver_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            version = ver_match.group(1) if ver_match else None

            # Find URL
            url_match = re.search(r'url\s*=\s*["\']([^"\']+)["\']', content)
            url = url_match.group(1) if url_match else None

            if url and version:
                # Replace {version} with actual version
                url = url.replace("{version}", version)
                recipes.append((name, url, path))

print(f"Found {len(recipes)} recipes with URLs")

# Download missing files
for name, url, path in recipes:
    # Extract filename from URL
    filename = os.path.basename(url)
    target = os.path.join(PKG_CACHE, filename)

    if os.path.exists(target):
        print(f"  ✅ {name}: already cached")
        continue

    print(f"  ⬇ {name}: downloading {filename}...")

    # Try direct first, then mirror
    for download_url in [url, MIRROR + url]:
        try:
            result = subprocess.run(
                ["curl", "-L", "--connect-timeout", "15", "-o", target, download_url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and os.path.getsize(target) > 100:
                print(f"    OK ({os.path.getsize(target)} bytes)")
                break
            else:
                # Remove failed download
                if os.path.exists(target):
                    os.remove(target)
        except Exception as e:
            if os.path.exists(target):
                os.remove(target)
            continue
    else:
        print(f"    ❌ FAILED")

print("\nDone!")
