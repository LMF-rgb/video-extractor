"""清晰度/格式选择逻辑

处理 yt-dlp 返回的格式列表，提供用户友好的清晰度选项。
"""

from dataclasses import dataclass


@dataclass
class QualityOption:
    """清晰度选项"""
    label: str         # 用户看到的中文标签
    format_str: str    # yt-dlp format selection string
    description: str   # 简短说明


# ── 默认清晰度选项 ─────────────────────────────────────
DEFAULT_QUALITY_OPTIONS: list[QualityOption] = [
    QualityOption(
        label="🎯 最佳质量（推荐）",
        format_str="bestvideo+bestaudio/best",
        description="自动选择最高画质+最佳音质",
    ),
    QualityOption(
        label="📺 1080P",
        format_str="bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        description="全高清，适合大部分需求",
    ),
    QualityOption(
        label="📱 720P",
        format_str="bestvideo[height<=720]+bestaudio/best[height<=720]",
        description="高清，文件较小",
    ),
    QualityOption(
        label="📱 480P",
        format_str="bestvideo[height<=480]+bestaudio/best[height<=480]",
        description="标清，省空间省流量",
    ),
    QualityOption(
        label="🎵 仅音频 (MP3)",
        format_str="bestaudio/best",
        description="只下载音频，提取为 MP3",
    ),
]


def get_format_str_by_label(label: str) -> str:
    """根据标签获取 format 字符串"""
    for opt in DEFAULT_QUALITY_OPTIONS:
        if opt.label == label:
            return opt.format_str
    return DEFAULT_QUALITY_OPTIONS[0].format_str  # 默认最佳


def get_quality_labels() -> list[str]:
    """获取所有清晰度标签列表"""
    return [opt.label for opt in DEFAULT_QUALITY_OPTIONS]


def parse_formats(info_dict: dict) -> list[dict]:
    """从 yt-dlp 信息字典中提取可读的格式列表

    Args:
        info_dict: yt-dlp extract_info 返回的信息

    Returns:
        格式列表，每项包含 {id, resolution, fps, codec, size, note}
    """
    formats = info_dict.get("formats", [])
    result = []
    seen = set()

    for fmt in formats:
        # 只取视频格式
        if fmt.get("vcodec") == "none":
            continue

        height = fmt.get("height") or 0
        if height == 0:
            continue

        key = f"{height}p"
        if key in seen:
            continue
        seen.add(key)

        filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0

        result.append({
            "id": fmt.get("format_id", ""),
            "resolution": f"{height}p",
            "fps": fmt.get("fps") or fmt.get("video_fps") or "?",
            "codec": fmt.get("vcodec", "?")[:20],
            "size_mb": round(filesize / 1024 / 1024, 1) if filesize else 0,
            "note": fmt.get("format_note", ""),
        })

    return sorted(result, key=lambda x: int(x["resolution"].replace("p", "")), reverse=True)
