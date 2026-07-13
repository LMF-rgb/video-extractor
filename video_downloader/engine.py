"""视频下载引擎

封装 yt-dlp，提供统一的下载、信息提取、进度回调接口。
"""

import os
import sys
import json
import threading
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime

import yt_dlp

from .platforms import detect_platform, PlatformConfig
from .formats import (
    get_format_str_by_label,
    get_quality_labels,
    parse_formats,
    QualityOption,
)
from .utils import (
    sanitize_filename,
    format_bytes,
    format_speed,
    format_eta,
    friendly_error,
    get_default_download_dir,
)


# ── 数据结构 ──────────────────────────────────────────


@dataclass
class VideoInfo:
    """视频信息（提取不下载）"""
    title: str
    url: str
    platform: str
    platform_icon: str
    duration: int          # 秒
    thumbnail: str
    uploader: str
    upload_date: str
    description: str
    formats: list[dict]    # 可用清晰度列表
    webpage_url: str


@dataclass
class DownloadProgress:
    """下载进度"""
    status: str = "idle"           # idle / downloading / done / error
    title: str = ""
    url: str = ""
    platform: str = ""
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_bytes: float = 0
    eta_seconds: int = 0
    percent: float = 0.0
    elapsed_seconds: float = 0
    output_path: str = ""
    error_msg: str = ""


@dataclass
class DownloadResult:
    """单个下载结果"""
    success: bool
    url: str
    title: str
    platform: str
    output_path: str = ""
    file_size: int = 0
    error: str = ""
    elapsed_seconds: float = 0


# ── 进度回调适配器 ────────────────────────────────────


class _ProgressHook:
    """将 yt-dlp 的 progress_hooks 回调转为统一的 DownloadProgress"""

    def __init__(self, url: str, callback: Callable[[DownloadProgress], None]):
        self.url = url
        self.callback = callback
        self.progress = DownloadProgress(url=url)
        self._start_time = None

    def __call__(self, d: dict):
        status = d.get("status", "")
        self.progress.status = status

        if status == "downloading":
            self.progress.title = d.get("info_dict", {}).get("title", "") or d.get("filename", "")
            self.progress.downloaded_bytes = d.get("downloaded_bytes", 0) or 0
            self.progress.total_bytes = d.get("total_bytes", 0) or d.get("total_bytes_estimate", 0) or 0
            self.progress.speed_bytes = d.get("speed", 0) or 0
            self.progress.eta_seconds = d.get("eta", 0) or 0
            if self.progress.total_bytes > 0:
                self.progress.percent = round(
                    self.progress.downloaded_bytes / self.progress.total_bytes * 100, 1
                )
            self.progress.elapsed_seconds = d.get("elapsed", 0) or 0

        elif status == "finished":
            self.progress.percent = 100.0
            self.progress.output_path = d.get("filename", "")

        elif status == "error":
            self.progress.error_msg = str(d.get("error", "未知错误"))

        self.callback(self.progress)


# ── 核心引擎 ──────────────────────────────────────────


class VideoExtractor:
    """视频提取器 - 主引擎"""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        cookie_file: Optional[str] = None,
        use_browser_cookies: Optional[str] = None,
        proxy: Optional[str] = None,
        auto_update: bool = True,
    ):
        """
        Args:
            output_dir: 视频保存目录（默认 ~/Videos/视频提取器）
            cookie_file: Netscape 格式 cookie 文件路径
            use_browser_cookies: 从浏览器导入 cookie，如 'chrome', 'firefox', 'edge'
            proxy: 代理地址，如 'http://127.0.0.1:7890'
            auto_update: 启动时自动检查 yt-dlp 更新
        """
        self.output_dir = output_dir or get_default_download_dir()
        self.cookie_file = cookie_file
        self.use_browser_cookies = use_browser_cookies
        self.proxy = proxy
        self.auto_update = auto_update

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 当前下载进度（用于外部轮询）
        self.current_progress: DownloadProgress = DownloadProgress()

    # ── 构建 yt-dlp 选项 ──────────────────────────────

    def _build_options(
        self,
        format_str: str = "bestvideo+bestaudio/best",
        output_template: str = "%(title)s.%(ext)s",
        playlist: bool = False,
        progress_callback: Optional[Callable] = None,
        extra: Optional[dict] = None,
    ) -> dict:
        """构建 yt-dlp 参数字典"""
        outtmpl = os.path.join(self.output_dir, output_template)

        opts = {
            "format": format_str,
            "outtmpl": outtmpl,
            "noplaylist": not playlist,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [],
            "ignoreerrors": False,
            "retries": 10,
            "fragment_retries": 20,
            "socket_timeout": 30,
            "extractor_retries": 5,
            "merge_output_format": "mp4",
            "concurrent_fragment_downloads": 8,
            "no_color": True,
            # 写入下载记录
            "writethumbnail": False,
            "writeinfojson": False,
        }

        # Cookie 来源
        if self.use_browser_cookies:
            opts["cookiesfrombrowser"] = (self.use_browser_cookies,)
        elif self.cookie_file:
            opts["cookiefile"] = self.cookie_file

        # 代理
        if self.proxy:
            opts["proxy"] = self.proxy

        # 进度回调
        if progress_callback:
            opts["progress_hooks"].append(progress_callback)

        # 合并额外选项
        if extra:
            opts.update(extra)

        return opts

    # ── 提取视频信息（不下载） ────────────────────────

    def extract_info(self, url: str) -> VideoInfo:
        """从 URL 提取视频信息（标题、清晰度、时长等）

        Args:
            url: 视频链接

        Returns:
            VideoInfo 包含视频元数据和可用格式列表

        Raises:
            Exception: 提取失败
        """
        platform = detect_platform(url)
        opts = self._build_options()

        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                raise RuntimeError(friendly_error(e)) from e

        # 如果是播放列表，取第一个视频
        if info.get("_type") == "playlist":
            entries = info.get("entries", [])
            if entries:
                info = entries[0]
            else:
                raise RuntimeError("播放列表为空")

        # 解析格式
        formats = parse_formats(info)

        return VideoInfo(
            title=info.get("title", "未知标题"),
            url=url,
            platform=platform.key if platform else "未知",
            platform_icon=platform.icon if platform else "❓",
            duration=info.get("duration", 0) or 0,
            thumbnail=info.get("thumbnail", ""),
            uploader=info.get("uploader", "") or info.get("channel", ""),
            upload_date=info.get("upload_date", ""),
            description=(info.get("description", "") or "")[:500],
            formats=formats,
            webpage_url=info.get("webpage_url", url),
        )

    # ── 下载单个视频 ──────────────────────────────────

    def download(
        self,
        url: str,
        quality_label: str = "",
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        audio_only: bool = False,
    ) -> DownloadResult:
        """下载单个视频

        Args:
            url: 视频链接
            quality_label: 清晰度标签（来自 get_quality_labels()），空=最佳
            progress_callback: 进度回调，接收 DownloadProgress 对象
            audio_only: 仅下载音频

        Returns:
            DownloadResult
        """
        platform = detect_platform(url)
        platform_name = platform.key if platform else "未知"

        format_str = get_format_str_by_label(quality_label) if quality_label else "bestvideo+bestaudio/best"
        if audio_only:
            format_str = "bestaudio/best"

        # 设置进度钩子
        hook = _ProgressHook(url, callback=progress_callback or (lambda p: None))
        self.current_progress = hook.progress
        self.current_progress.platform = platform_name

        # 音频专用额外选项
        extra = {}
        if audio_only:
            extra["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        opts = self._build_options(
            format_str=format_str,
            progress_callback=hook,
            extra=extra,
        )

        start_time = datetime.now()

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info.get("_type") == "playlist":
                    entries = info.get("entries", [])
                    if entries:
                        info = entries[0]

                title = info.get("title", "未知标题")
                # yt-dlp 实际输出路径
                output_path = hook.progress.output_path

                # 尝试获取真实输出路径
                if not output_path or not os.path.exists(output_path):
                    # 推测路径
                    ext = "mp3" if audio_only else "mp4"
                    safe_title = sanitize_filename(title)
                    output_path = os.path.join(self.output_dir, f"{safe_title}.{ext}")
                    if not os.path.exists(output_path):
                        # 搜索目录中最近创建的文件
                        output_path = self._find_latest_file()

        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            return DownloadResult(
                success=False,
                url=url,
                title="",
                platform=platform_name,
                error=friendly_error(e),
                elapsed_seconds=elapsed,
            )

        elapsed = (datetime.now() - start_time).total_seconds()
        file_size = os.path.getsize(output_path) if output_path and os.path.exists(output_path) else 0

        # 标记完成
        hook.progress.status = "done"
        hook.progress.percent = 100.0
        hook.progress.output_path = output_path
        progress_callback and progress_callback(hook.progress)

        return DownloadResult(
            success=True,
            url=url,
            title=title,
            platform=platform_name,
            output_path=output_path or "",
            file_size=file_size,
            elapsed_seconds=elapsed,
        )

    # ── 批量下载 ──────────────────────────────────────

    def batch_download(
        self,
        urls: list[str],
        quality_label: str = "",
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        audio_only: bool = False,
    ) -> list[DownloadResult]:
        """批量下载多个视频（串行）

        Args:
            urls: 视频链接列表
            quality_label: 统一清晰度
            progress_callback: 整体进度回调
            audio_only: 仅音频

        Returns:
            下载结果列表
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            if progress_callback:
                p = DownloadProgress(
                    url=url,
                    title=f"排队中 ({i+1}/{total})",
                    status="downloading",
                )
                progress_callback(p)

            result = self.download(
                url=url,
                quality_label=quality_label,
                progress_callback=progress_callback,
                audio_only=audio_only,
            )
            results.append(result)

        return results

    # ── 工具方法 ──────────────────────────────────────

    def _find_latest_file(self) -> str:
        """在输出目录中找最近创建的文件"""
        try:
            files = [f for f in os.listdir(self.output_dir)
                     if os.path.isfile(os.path.join(self.output_dir, f))]
            if not files:
                return ""
            latest = max(files, key=lambda f: os.path.getctime(
                os.path.join(self.output_dir, f)))
            return os.path.join(self.output_dir, latest)
        except Exception:
            return ""

    @staticmethod
    def get_quality_labels() -> list[str]:
        """获取所有可选清晰度标签"""
        return get_quality_labels()

    @staticmethod
    def check_ffmpeg() -> bool:
        """检查 FFmpeg 是否可用"""
        try:
            from yt_dlp.postprocessor import FFmpegPostProcessor
            return FFmpegPostProcessor().available
        except ImportError:
            from yt_dlp.utils import FFmpegPostProcessor
            return FFmpegPostProcessor().available

    @staticmethod
    def check_version() -> str:
        """获取 yt-dlp 版本"""
        return yt_dlp.version.__version__

    @staticmethod
    def update_ytdlp() -> tuple[bool, str]:
        """更新 yt-dlp 到最新版

        Returns:
            (是否成功, 消息)
        """
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                return True, "yt-dlp 已更新到最新版本 ✅"
            return False, f"更新失败: {result.stderr[:200]}"
        except Exception as e:
            return False, f"更新异常: {e}"
