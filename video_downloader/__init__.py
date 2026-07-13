"""全平台视频提取器 - 共享核心引擎

基于 yt-dlp 的视频下载模块，支持:
- B站 (bilibili)  - 抖音 (douyin)    - YouTube
- 小红书 (xiaohongshu)  - 快手 (kuaishou)
- 微博 (weibo)  - 西瓜视频 (xigua)
"""

from .engine import VideoExtractor
from .platforms import detect_platform, PLATFORM_CONFIG

__version__ = "1.0.0"
__all__ = ["VideoExtractor", "detect_platform", "PLATFORM_CONFIG"]
