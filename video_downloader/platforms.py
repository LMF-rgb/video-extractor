"""平台识别与配置

每个平台的 URL 特征、cookie 策略、特殊处理逻辑。
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlatformConfig:
    """单个平台的配置"""
    name: str                    # 显示名称
    key: str                     # 内部标识
    domains: list[str]           # URL 域名匹配列表
    patterns: list[str]          # URL 正则匹配
    icon: str                    # emoji 图标
    need_cookies: bool = False   # 是否需要 cookie 才能高清
    cookie_note: str = ""        # cookie 提示文字
    special_handling: str = ""   # 特殊处理说明


# ── 平台配置表 ──────────────────────────────────────────
PLATFORMS: list[PlatformConfig] = [
    PlatformConfig(
        name="B站",
        key="bilibili",
        domains=["bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"],
        patterns=[r"bilibili\.com/video/(BV[\w]+|av\d+)", r"b23\.tv/[\w]+"],
        icon="📺",
        need_cookies=True,
        cookie_note="1080P+高清需要B站登录Cookie，否则只能下载720P",
        special_handling="番剧/影视需要大会员；CDN偶尔403需重试",
    ),
    PlatformConfig(
        name="抖音",
        key="douyin",
        domains=["douyin.com", "www.douyin.com", "v.douyin.com", "tiktok.com"],
        patterns=[r"douyin\.com/(video|user|note)/[\w]+", r"v\.douyin\.com/[\w]+"],
        icon="🎵",
        need_cookies=True,
        cookie_note="部分视频需要抖音登录Cookie",
        special_handling="自动去除水印；短链接自动解析",
    ),
    PlatformConfig(
        name="YouTube",
        key="youtube",
        domains=["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"],
        patterns=[r"youtube\.com/(watch\?v=|shorts/)[\w\-]+", r"youtu\.be/[\w\-]+"],
        icon="▶️",
        need_cookies=True,
        cookie_note="年龄限制视频需要登录；部分地区需要代理",
        special_handling="自动合并最佳视频+音频流；支持字幕下载",
    ),
    PlatformConfig(
        name="小红书",
        key="xiaohongshu",
        domains=["xiaohongshu.com", "www.xiaohongshu.com", "xhslink.com"],
        patterns=[r"xiaohongshu\.com/(discovery/item|explore)/[\w]+", r"xhslink\.com/[\w]+"],
        icon="📕",
        need_cookies=True,
        cookie_note="小红书需要登录Cookie才能访问内容",
        special_handling="自动区分图文/视频；图文仅保存封面",
    ),
    PlatformConfig(
        name="快手",
        key="kuaishou",
        domains=["kuaishou.com", "www.kuaishou.com", "v.kuaishou.com"],
        patterns=[r"kuaishou\.com/(short-video|f)/[\w]+", r"v\.kuaishou\.com/[\w]+"],
        icon="⚡",
        need_cookies=False,
        special_handling="无水印链接自动替换",
    ),
    PlatformConfig(
        name="微博",
        key="weibo",
        domains=["weibo.com", "www.weibo.com", "m.weibo.cn", "t.cn"],
        patterns=[r"weibo\.(com|cn)/(tv/show|detail)/[\w]+", r"t\.cn/[\w]+"],
        icon="📢",
        need_cookies=True,
        cookie_note="微博视频通常需要登录才能获取",
        special_handling="短链接 t.cn 自动展开",
    ),
    PlatformConfig(
        name="西瓜视频",
        key="xigua",
        domains=["xigua.com", "www.xigua.com", "ixigua.com"],
        patterns=[r"xigua\.com/(video/)?[\d]+", r"ixigua\.com/[\w]+"],
        icon="🍉",
        need_cookies=False,
        special_handling="与抖音共用部分接口",
    ),
]

# 构建快速查找字典
PLATFORM_CONFIG: dict[str, PlatformConfig] = {p.key: p for p in PLATFORMS}


def detect_platform(url: str) -> Optional[PlatformConfig]:
    """根据 URL 自动识别平台

    Args:
        url: 视频链接

    Returns:
        匹配的 PlatformConfig，未识别返回 None
    """
    url_lower = url.lower().strip()
    for platform in PLATFORMS:
        for domain in platform.domains:
            if domain in url_lower:
                return platform
        for pattern in platform.patterns:
            if re.search(pattern, url_lower):
                return platform
    return None


def get_platform_supports_text() -> str:
    """生成支持的平台说明文本"""
    lines = ["支持的平台："]
    for p in PLATFORMS:
        extra = f" ({p.special_handling})" if p.special_handling else ""
        lines.append(f"  {p.icon} {p.name} {extra}")
    return "\n".join(lines)
