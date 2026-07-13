# 在 Google Colab 中运行此脚本构建 APK
# 1. 把这个文件上传到 Colab
# 2. 把整个项目文件夹打包为 zip，上传到 Colab
# 3. 运行此脚本

import os, sys, subprocess, zipfile, shutil

PROJECT_DIR = "/content/video-extractor"

# ── 步骤1：安装环境 ──
print("📦 安装系统依赖...")
os.system("apt-get update -qq && apt-get install -y -qq git zip unzip openjdk-17-jdk python3-pip autoconf libtool cmake libffi-dev libssl-dev build-essential libltdl-dev > /dev/null 2>&1")
os.system("pip install cython buildozer -q")
print("✅ 环境就绪")

# ── 步骤2：上传项目 ──
from google.colab import files
print("\n📁 请上传项目 zip 文件...")
uploaded = files.upload()

zip_name = list(uploaded.keys())[0]
print(f"上传: {zip_name}")

if os.path.exists(PROJECT_DIR):
    shutil.rmtree(PROJECT_DIR)

with zipfile.ZipFile(zip_name, 'r') as zf:
    zf.extractall(PROJECT_DIR)
print("✅ 项目解压完成")

# ── 步骤3：构建 APK ──
spec_dir = f"{PROJECT_DIR}/android"
assert os.path.exists(f"{spec_dir}/buildozer.spec"), "找不到 buildozer.spec！"

os.chdir(spec_dir)
print("\n🔨 开始构建 APK（首次约20-30分钟）...")
result = subprocess.run(["buildozer", "android", "debug"])

if result.returncode != 0:
    print("❌ 构建失败！请检查上方日志")
    sys.exit(1)

# ── 步骤4：下载 ──
import glob
apks = glob.glob(f"{spec_dir}/bin/*.apk")
if apks:
    apk_path = apks[0]
    size_mb = os.path.getsize(apk_path) / 1024 / 1024
    print(f"\n🎉 APK 构建成功！{size_mb:.1f} MB")
    files.download(apk_path)
else:
    print("❌ 找不到生成的 APK 文件")
