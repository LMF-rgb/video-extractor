#!/usr/bin/env python3
"""在 Google Colab 中构建 APK 的脚本

使用方法：
1. 把整个项目文件夹（003-video-extractor）打包为 zip
2. 上传到 Google Drive
3. 在 Colab 中运行此脚本

或者直接把此文件内容复制到 Colab notebook 中运行。
"""

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# ── 配置 ──────────────────────────────────────
PROJECT_NAME = "video-extractor"
ZIP_PATH = "/content/drive/MyDrive/003-video-extractor.zip"  # 修改为你的zip路径

# ── 安装依赖 ──────────────────────────────────


def install_deps():
    """安装 Buildozer 和系统依赖"""
    print("=" * 50)
    print("📦 安装系统依赖...")
    print("=" * 50)

    # 更新包列表
    subprocess.run(["apt-get", "update", "-qq"], check=True)

    # Buildozer 需要的系统包
    packages = [
        "git", "zip", "unzip", "openjdk-17-jdk", "python3-pip",
        "autoconf", "libtool", "pkg-config", "zlib1g-dev",
        "libncurses5-dev", "libncursesw5-dev", "libtinfo5",
        "cmake", "libffi-dev", "libssl-dev",
        "build-essential", "libltdl-dev",
    ]
    subprocess.run(["apt-get", "install", "-y", "-qq"] + packages, check=True)

    # Cython (Buildozer 需要)
    subprocess.run(["pip", "install", "cython", "buildozer"], check=True)

    print("✅ 依赖安装完成")


def prepare_project():
    """准备项目文件"""
    print()
    print("=" * 50)
    print("📁 准备项目文件...")
    print("=" * 50)

    # 如果项目已经存在，先删除
    if os.path.exists(f"/content/{PROJECT_NAME}"):
        shutil.rmtree(f"/content/{PROJECT_NAME}")

    # 解压项目
    if os.path.exists(ZIP_PATH):
        print(f"解压 {ZIP_PATH}...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
            zf.extractall(f"/content/{PROJECT_NAME}")
    else:
        print(f"⚠️ 未找到 {ZIP_PATH}")
        print("请将项目zip上传到Google Drive，或手动创建项目目录")
        print()
        print("创建项目结构...")
        os.makedirs(f"/content/{PROJECT_NAME}/video_downloader", exist_ok=True)
        os.makedirs(f"/content/{PROJECT_NAME}/android", exist_ok=True)

        # 提示用户上传文件
        print("""
        ╔══════════════════════════════════════════════╗
        ║  请将以下文件上传到对应目录:               ║
        ║  video_downloader/  → 所有 .py 文件        ║
        ║  android/main.py                            ║
        ║  android/buildozer.spec                     ║
        ╚══════════════════════════════════════════════╝
        """)

    # 确认 buildozer.spec 存在
    spec_path = f"/content/{PROJECT_NAME}/android/buildozer.spec"
    if not os.path.exists(spec_path):
        print(f"❌ 找不到 buildozer.spec: {spec_path}")
        print("请在 android/ 目录下创建 buildozer.spec 文件")
        sys.exit(1)

    print("✅ 项目准备完成")
    return spec_path


def build_apk(spec_path):
    """构建 APK"""
    print()
    print("=" * 50)
    print("🔨 开始构建 APK...")
    print("⏱  首次构建约需 20-30 分钟")
    print("=" * 50)

    android_dir = os.path.dirname(spec_path)
    os.chdir(android_dir)

    # 运行 Buildozer
    result = subprocess.run(
        ["buildozer", "android", "debug"],
        cwd=android_dir,
    )

    if result.returncode != 0:
        print()
        print("❌ APK 构建失败！")
        print("请检查上方日志排查错误")
        return None

    # 查找生成的 APK
    apk_patterns = [
        f"{android_dir}/bin/*.apk",
        f"/content/{PROJECT_NAME}/android/bin/*.apk",
    ]

    apk_path = None
    for pattern in apk_patterns:
        import glob
        apks = glob.glob(pattern)
        if apks:
            apk_path = apks[0]
            break

    return apk_path


def main():
    install_deps()
    spec_path = prepare_project()

    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  准备就绪，开始构建？                       ║")
    print("║  这将需要 20-30 分钟                        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # 在 Colab 中自动执行，本地运行时确认
    if "COLAB_GPU" in os.environ:
        apk_path = build_apk(spec_path)
    else:
        resp = input("输入 'y' 开始构建: ").strip().lower()
        if resp != 'y':
            print("已取消")
            return
        apk_path = build_apk(spec_path)

    if apk_path:
        print()
        print("=" * 50)
        print(f"🎉 APK 构建成功！")
        print(f"📱 文件位置: {apk_path}")
        print(f"📦 文件大小: {os.path.getsize(apk_path) / 1024 / 1024:.1f} MB")
        print()
        print("下载方法:")
        print(f"  from google.colab import files")
        print(f"  files.download('{apk_path}')")
        print("=" * 50)
    else:
        print("❌ 构建失败，请检查日志")


if __name__ == "__main__":
    main()
