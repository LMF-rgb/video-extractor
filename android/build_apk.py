"""一键构建 APK - Python 脚本，避免 bash 变量问题"""
import os, sys, re, subprocess, shutil

P4A_DIR = "/root/video-extractor/android/.buildozer/android/platform/python-for-android"
ANDROID_DIR = "/root/video-extractor/android"
BUILD_DIR = "/root/video-extractor/android/.buildozer/android/platform/build-arm64-v8a_armeabi-v7a"

# Step 1: Pre-clone p4a from gitee
print("Step 1: Cloning python-for-android from gitee...")
if os.path.exists(P4A_DIR):
    shutil.rmtree(P4A_DIR)
os.makedirs(os.path.dirname(P4A_DIR), exist_ok=True)

# Try GitHub via ghproxy first, then gitee as fallback
urls = [
    "https://ghproxy.net/https://github.com/kivy/python-for-android.git",
    "https://gitee.com/mirrors/python-for-android.git",
]
clone_ok = False
for url in urls:
    print(f"  Trying: {url[:60]}...")
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "-b", "master", url, P4A_DIR],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode == 0:
        clone_ok = True
        break
    else:
        print(f"  Failed: {r.stderr[:100]}")
        if os.path.exists(P4A_DIR):
            shutil.rmtree(P4A_DIR)

if not clone_ok:
    print("All clone URLs failed")
    sys.exit(1)
print("  Done")

# Step 2: Patch Python and Kivy versions
print("Step 2: Patching recipes...")
recipes = os.path.join(P4A_DIR, "pythonforandroid", "recipes")
for recipe in ["hostpython3", "python3"]:
    path = os.path.join(recipes, recipe, "__init__.py")
    if not os.path.exists(path):
        continue
    with open(path, "r") as f:
        content = f.read()
    content = re.sub(r'version\s*=\s*["\']3\.\d+\.\d+["\']', 'version = "3.12.10"', content)
    content = re.sub(r'\(3,\s*\d+,\s*\d+\)', '(3, 12, 10)', content)
    with open(path, "w") as f:
        f.write(content)
    print(f"  Patched {recipe}")

kivy = os.path.join(recipes, "kivy", "__init__.py")
if os.path.exists(kivy):
    with open(kivy, "r") as f:
        content = f.read()
    content = re.sub(r'version\s*=\s*["\'][^"\']+["\']', 'version = "2.3.1"', content)
    with open(kivy, "w") as f:
        f.write(content)
    print("  Patched kivy")

# Step 3: Clean old build artifacts
print("Step 3: Cleaning old builds...")
for d in [os.path.join(BUILD_DIR, "build"), os.path.join(BUILD_DIR, "dists")]:
    if os.path.exists(d):
        shutil.rmtree(d)
print("  Done")

# Step 4: Run Buildozer
print("Step 4: Building APK...")
os.chdir(ANDROID_DIR)
os.environ["PIP_BREAK_SYSTEM_PACKAGES"] = "1"

proc = subprocess.Popen(
    ["buildozer", "android", "debug"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)
proc.stdin.write("y\n")
proc.stdin.flush()

# Stream output
for line in proc.stdout:
    line = line.strip()
    if line and ("Error" in line or "failed" in line or "SUCCESS" in line or
                 "already cached" in line or "Unpacking" in line or
                 "Building" in line or "APK" in line or "compil" in line.lower()):
        print(f"  {line[:150]}")

proc.wait()
print(f"\nBuild exit: {proc.returncode}")

# Step 5: Find APK
for root, dirs, files in os.walk(ANDROID_DIR):
    for f in files:
        if f.endswith(".apk"):
            apk = os.path.join(root, f)
            size_mb = os.path.getsize(apk) / 1024 / 1024
            print(f"\n🎉 APK: {apk} ({size_mb:.1f} MB)")
            sys.exit(0)

print("No APK found")
