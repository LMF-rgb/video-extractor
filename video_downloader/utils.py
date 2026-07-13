"""工具函数

文件名清理、字节格式化、错误友好提示等。
"""

import re
import os
from datetime import datetime


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """清理文件名，移除非法字符

    Args:
        name: 原始文件名
        max_len: 最大长度

    Returns:
        安全的文件名
    """
    # 移除 Windows 文件名字符
    illegal = r'[<>:"/\\|?*\r\n\t]'
    name = re.sub(illegal, "_", name)
    # 移除连续空格
    name = re.sub(r"\s+", " ", name).strip()
    # 移除首尾的点和空格
    name = name.strip(". ")
    # 截断
    if len(name) > max_len:
        name = name[:max_len - 3] + "..."
    # 空文件名保护
    if not name:
        name = f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return name


def format_bytes(size: int) -> str:
    """格式化字节数为可读字符串"""
    if size is None or size <= 0:
        return "未知"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """格式化下载速度"""
    if bytes_per_sec is None or bytes_per_sec <= 0:
        return "--"
    return f"{format_bytes(int(bytes_per_sec))}/s"


def format_eta(seconds: int) -> str:
    """格式化剩余时间"""
    if seconds is None or seconds <= 0:
        return "--"
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        return f"{seconds // 60}分{seconds % 60}秒"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}时{m}分"


def ensure_output_dir(directory: str) -> str:
    """确保输出目录存在，不存在则创建"""
    os.makedirs(directory, exist_ok=True)
    return directory


def get_default_download_dir() -> str:
    """获取默认下载目录"""
    return os.path.join(os.path.expanduser("~"), "Videos", "视频提取器")


def friendly_error(exc: Exception) -> str:
    """将 yt-dlp 异常转为用户友好的错误信息

    Args:
        exc: 原始异常

    Returns:
        用户可读的错误信息
    """
    msg = str(exc).lower()

    if "403" in msg or "forbidden" in msg:
        return "⚠️ 访问被拒绝(403)。可能需要登录Cookie或该视频有地域限制。"
    elif "404" in msg or "not found" in msg:
        return "❌ 视频不存在或已被删除(404)。请检查链接是否正确。"
    elif "copyright" in msg or "blocked" in msg:
        return "🚫 该视频因版权原因被屏蔽，无法下载。"
    elif "login" in msg or "cookie" in msg:
        return "🔐 需要登录才能下载。请在设置中导入浏览器Cookie。"
    elif "private" in msg:
        return "🔒 该视频为私密视频，无法下载。"
    elif "age" in msg and "restrict" in msg:
        return "🔞 该视频有年龄限制，需要登录验证。"
    elif "network" in msg or "timeout" in msg or "connection" in msg:
        return "🌐 网络连接失败。请检查网络或尝试使用代理。"
    elif "geoblock" in msg or "geo" in msg:
        return "🌍 该视频有地域限制，当前地区无法访问。"
    elif "ffmpeg" in msg:
        return "🔧 缺少 FFmpeg。请安装 FFmpeg 后重试。"
    elif "unavailable" in msg or "removed" in msg:
        return "🚫 视频已失效或被删除。"
    else:
        # 返回原始错误的前200字符
        short = str(exc)[:200]
        return f"❌ 下载失败: {short}"
