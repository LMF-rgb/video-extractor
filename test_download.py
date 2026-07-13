#!/usr/bin/env python3
"""测试脚本 - 验证核心引擎和平台识别"""

import sys
import os

# 确保能导入 video_downloader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_downloader import VideoExtractor, detect_platform
from video_downloader.formats import get_quality_labels
from video_downloader.utils import get_default_download_dir


def test_platform_detection():
    """测试平台识别"""
    print("=" * 50)
    print("📋 测试平台 URL 识别")
    print("=" * 50)

    test_urls = [
        ("https://www.bilibili.com/video/BV1xx411c7mD", "B站 标准链接"),
        ("https://b23.tv/xxxxx", "B站 短链接"),
        ("https://v.douyin.com/xxxxx/", "抖音 短链接"),
        ("https://www.douyin.com/video/123456", "抖音 标准链接"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "YouTube 标准"),
        ("https://youtu.be/dQw4w9WgXcQ", "YouTube 短链接"),
        ("https://www.xiaohongshu.com/explore/xxxxx", "小红书"),
        ("https://www.kuaishou.com/short-video/xxxxx", "快手"),
        ("https://www.ixigua.com/123456", "西瓜视频"),
        ("https://weibo.com/tv/show/123456", "微博"),
        ("https://www.unknown-site.com/video/123", "未知平台"),
    ]

    for url, desc in test_urls:
        platform = detect_platform(url)
        if platform:
            print(f"  ✅ {desc}: → {platform.icon} {platform.name} ({platform.key})")
        else:
            print(f"  ⚠️  {desc}: → 未识别")

    print()


def test_quality_labels():
    """测试清晰度选项"""
    print("=" * 50)
    print("🎯 可选清晰度")
    print("=" * 50)
    for label in get_quality_labels():
        print(f"  • {label}")
    print()


def test_extractor_init():
    """测试引擎初始化"""
    print("=" * 50)
    print("🔧 引擎初始化")
    print("=" * 50)

    extractor = VideoExtractor()
    print(f"  输出目录: {extractor.output_dir}")
    print(f"  yt-dlp 版本: {extractor.check_version()}")
    print(f"  FFmpeg 可用: {extractor.check_ffmpeg()}")
    print()


def test_info_extract():
    """测试信息提取（需要一个真实链接）"""
    print("=" * 50)
    print("ℹ️  视频信息提取测试")
    print("=" * 50)

    # 使用一个公开的短测试视频
    test_url = input("请输入一个测试链接（回车跳过）: ").strip()
    if not test_url:
        print("  ⏭ 跳过信息提取测试")
        return

    extractor = VideoExtractor()
    try:
        info = extractor.extract_info(test_url)
        print(f"  标题: {info.title}")
        print(f"  平台: {info.platform_icon} {info.platform}")
        print(f"  时长: {info.duration}秒")
        print(f"  上传者: {info.uploader}")
        print(f"  可用格式: {len(info.formats)} 个")
        for fmt in info.formats[:5]:
            print(f"    - {fmt['resolution']} {fmt['codec']} ({fmt['size_mb']}MB)")
    except Exception as e:
        print(f"  ❌ 提取失败: {e}")


def main():
    print()
    print("🎬 全平台视频提取器 - 测试套件")
    print()

    test_platform_detection()
    test_quality_labels()
    test_extractor_init()
    test_info_extract()

    print()
    print("✅ 测试完成！运行 `python desktop/app.py` 启动桌面版")
    print(f"📁 下载目录: {get_default_download_dir()}")
    print()


if __name__ == "__main__":
    main()
