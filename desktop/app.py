#!/usr/bin/env python3
"""全平台视频提取器 - 桌面版

基于 Gradio 的 Web GUI，双击启动后在浏览器中使用。
"""

import os
import sys
import threading
import queue
import time
import webbrowser

# 将项目根目录加入 Python 路径（支持直接运行和打包后运行）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gradio as gr

from video_downloader import VideoExtractor, detect_platform
from video_downloader.formats import get_quality_labels
from video_downloader.utils import (
    format_bytes,
    format_speed,
    format_eta,
    get_default_download_dir,
    ensure_output_dir,
)
from video_downloader.platforms import PLATFORMS


# ── 样式 ─────────────────────────────────────────────

CUSTOM_CSS = """
.gradio-container {
    max-width: 800px !important;
    margin: auto !important;
}
.header {
    text-align: center;
    margin-bottom: 20px;
}
.header h1 {
    font-size: 2em;
    margin: 0;
}
.platform-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin: 10px 0;
}
.platform-badge {
    background: #2a2a2a;
    border: 1px solid #444;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.85em;
}
.download-item {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
.progress-bar-wrap {
    background: #333;
    border-radius: 10px;
    height: 20px;
    overflow: hidden;
    margin: 8px 0;
}
.progress-bar-fill {
    background: linear-gradient(90deg, #4CAF50, #8BC34A);
    height: 100%;
    border-radius: 10px;
    transition: width 0.3s;
}
.error-box {
    background: #3a1a1a;
    border: 1px solid #f44336;
    border-radius: 8px;
    padding: 12px;
    color: #ff6b6b;
}
.success-box {
    background: #1a3a1a;
    border: 1px solid #4CAF50;
    border-radius: 8px;
    padding: 12px;
    color: #8BC34A;
}
"""

PLATFORM_BADGES_HTML = """
<div class="platform-badges">
    {badges}
</div>
""".format(
    badges="\n".join(
        f'<span class="platform-badge">{p.icon} {p.name}</span>'
        for p in PLATFORMS
    )
)

HEADER_HTML = f"""
<div class="header">
    <h1>🎬 全平台视频提取器</h1>
    <p>粘贴视频链接 → 选择清晰度 → 一键下载 | 开源免费 永不收费</p>
    {PLATFORM_BADGES_HTML}
</div>
"""


# ── 全局状态 ─────────────────────────────────────────

class AppState:
    """应用全局状态"""
    def __init__(self):
        self.extractor: VideoExtractor = None
        self.url_list: list[str] = []
        self.downloading = False
        self.cancel_flag = False
        self.history: list[dict] = []
        self.progress_queue = queue.Queue()


app_state = AppState()


def get_extractor(output_dir: str, browser_cookie: str, proxy: str) -> VideoExtractor:
    """获取或创建 VideoExtractor 实例"""
    out = output_dir.strip() or get_default_download_dir()
    ensure_output_dir(out)
    cookie = browser_cookie.strip() if browser_cookie.strip() else None
    proxy_url = proxy.strip() if proxy.strip() else None
    app_state.extractor = VideoExtractor(
        output_dir=out,
        use_browser_cookies=cookie if cookie else None,
        proxy=proxy_url,
    )
    return app_state.extractor


# ── 事件处理 ─────────────────────────────────────────

def add_url(url: str, url_list_str: str) -> tuple[str, str]:
    """添加单个 URL 到列表"""
    url = url.strip()
    if not url:
        return "", url_list_str

    if url in app_state.url_list:
        return "", url_list_str  # 不重复添加

    app_state.url_list.append(url)
    return "", "\n".join(app_state.url_list)


def remove_url(index_str: str) -> str:
    """从列表中移除 URL"""
    try:
        idx = int(index_str) - 1  # 前端显示从1开始
        if 0 <= idx < len(app_state.url_list):
            app_state.url_list.pop(idx)
    except (ValueError, IndexError):
        pass
    return "\n".join(app_state.url_list)


def clear_list() -> str:
    """清空 URL 列表"""
    app_state.url_list.clear()
    return ""


def paste_urls(text: str) -> str:
    """从文本框批量导入 URL（一行一个）"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    added = 0
    for line in lines:
        if line not in app_state.url_list:
            app_state.url_list.append(line)
            added += 1
    return "\n".join(app_state.url_list)


def start_download(
    url_list_str: str,
    quality: str,
    output_dir: str,
    audio_only: bool,
    browser_cookie: str,
    proxy: str,
) -> tuple[str, str, str]:
    """开始下载，在后台线程执行"""
    urls = [u.strip() for u in url_list_str.split("\n") if u.strip()]
    if not urls:
        return "", "⚠️ 请先添加视频链接", ""

    if app_state.downloading:
        return "", "⏳ 正在下载中，请等待当前任务完成...", ""

    app_state.downloading = True
    app_state.cancel_flag = False

    extractor = get_extractor(output_dir, browser_cookie, proxy)

    # 启动后台下载线程
    thread = threading.Thread(
        target=_download_thread,
        args=(urls, quality, audio_only),
        daemon=True,
    )
    thread.start()

    return "", f"🚀 开始下载 {len(urls)} 个视频...", ""


def _download_thread(urls: list[str], quality_label: str, audio_only: bool):
    """后台下载线程"""
    extractor = app_state.extractor
    results = []
    total = len(urls)

    for i, url in enumerate(urls):
        if app_state.cancel_flag:
            break

        platform = detect_platform(url)
        platform_name = f"{platform.icon} {platform.name}" if platform else "❓ 未知平台"

        # 发送开始信息
        app_state.progress_queue.put({
            "type": "start",
            "index": i,
            "total": total,
            "url": url,
            "platform": platform_name,
        })

        # 定义进度回调
        def on_progress(prog):
            app_state.progress_queue.put({
                "type": "progress",
                "index": i,
                "total": total,
                "percent": prog.percent,
                "downloaded": format_bytes(prog.downloaded_bytes),
                "total_size": format_bytes(prog.total_bytes),
                "speed": format_speed(prog.speed_bytes),
                "eta": format_eta(prog.eta_seconds),
                "title": prog.title,
            })

        result = extractor.download(
            url=url,
            quality_label=quality_label,
            progress_callback=on_progress,
            audio_only=audio_only,
        )
        results.append(result)

        if result.success:
            app_state.progress_queue.put({
                "type": "done",
                "index": i,
                "total": total,
                "title": result.title,
                "path": result.output_path,
                "size": format_bytes(result.file_size),
                "time": f"{result.elapsed_seconds:.1f}秒",
            })
            app_state.history.append({
                "url": url,
                "title": result.title,
                "path": result.output_path,
                "size": result.file_size,
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            app_state.progress_queue.put({
                "type": "error",
                "index": i,
                "total": total,
                "url": url,
                "error": result.error,
            })

    app_state.progress_queue.put({"type": "all_done", "total": len(results)})
    app_state.downloading = False


def cancel_download() -> str:
    """取消下载"""
    app_state.cancel_flag = True
    return "⏹ 正在取消..."

# ── UI 构建 ───────────────────────────────────────────


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面"""
    with gr.Blocks(
        title="全平台视频提取器",
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="green"),
    ) as app:
        # 隐藏 Gradio 底部
        gr.HTML(HEADER_HTML)

        with gr.Row():
            with gr.Column(scale=4):
                url_input = gr.Textbox(
                    label="🔗 视频链接",
                    placeholder="粘贴视频链接到这里... 支持 B站 | 抖音 | YouTube | 小红书 | 快手 | 微博 | 西瓜视频",
                    lines=1,
                )
            with gr.Column(scale=1):
                add_btn = gr.Button("➕ 添加", variant="primary")
                paste_btn = gr.Button("📋 批量粘贴")

        # URL 列表
        url_list = gr.Textbox(
            label="📝 下载队列（一行一个链接，可手动编辑）",
            lines=5,
            placeholder="https://www.bilibili.com/video/BV...\nhttps://www.youtube.com/watch?v=...\nhttps://v.douyin.com/...",
        )

        # 操作栏
        with gr.Row():
            quality_dropdown = gr.Dropdown(
                label="🎯 清晰度",
                choices=get_quality_labels(),
                value=get_quality_labels()[0],
                scale=3,
            )
            audio_checkbox = gr.Checkbox(
                label="🎵 仅音频",
                value=False,
                scale=1,
            )

        with gr.Row():
            output_dir = gr.Textbox(
                label="📁 保存目录",
                value=get_default_download_dir(),
                scale=4,
            )
            browser_cookie = gr.Dropdown(
                label="🍪 浏览器Cookie",
                choices=["", "chrome", "firefox", "edge", "brave", "opera"],
                value="",
                scale=1,
                info="高清需要",
            )

        with gr.Row():
            proxy_input = gr.Textbox(
                label="🌐 代理（可选）",
                placeholder="http://127.0.0.1:7890",
                scale=2,
            )

        # 按钮
        with gr.Row():
            download_btn = gr.Button("⬇️ 开始下载", variant="primary", size="lg", scale=3)
            clear_btn = gr.Button("🗑 清空列表", size="lg", scale=1)
            cancel_btn = gr.Button("⏹ 取消", variant="stop", size="lg", scale=1)

        # 状态区
        status_text = gr.Markdown("")

        # 进度显示
        progress_html = gr.HTML("")

        # 下载历史
        history_md = gr.Markdown("")

        # ── 事件绑定 ──────────────────────────────────

        add_btn.click(
            fn=add_url,
            inputs=[url_input, url_list],
            outputs=[url_input, url_list],
        )

        url_input.submit(
            fn=add_url,
            inputs=[url_input, url_list],
            outputs=[url_input, url_list],
        )

        paste_btn.click(
            fn=paste_urls,
            inputs=[url_input],
            outputs=[url_list],
        )

        clear_btn.click(
            fn=clear_list,
            inputs=[],
            outputs=[url_list],
        ).then(
            fn=lambda: "", inputs=[], outputs=[status_text],
        )

        download_btn.click(
            fn=start_download,
            inputs=[url_list, quality_dropdown, output_dir, audio_checkbox, browser_cookie, proxy_input],
            outputs=[url_list, status_text, progress_html],
        )

        cancel_btn.click(
            fn=cancel_download,
            inputs=[],
            outputs=[status_text],
        )

    return app


# ── 启动 ─────────────────────────────────────────────


def main():
    import socket

    app = create_ui()

    # 找可用端口
    port = 7860
    for p in range(7860, 7870):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", p))
                port = p
                break
        except OSError:
            continue

    print(f"""
╔══════════════════════════════════════════╗
║    🎬 全平台视频提取器 v1.0              ║
║    基于 yt-dlp + Gradio                 ║
║                                          ║
║    浏览器将自动打开，如未打开请访问:     ║
║    http://127.0.0.1:{port}                ║
║                                          ║
║    支持: B站 抖音 YouTube 小红书         ║
║          快手 微博 西瓜视频              ║
╚══════════════════════════════════════════╝
    """)

    # 自动打开浏览器
    webbrowser.open(f"http://127.0.0.1:{port}")

    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        show_error=True,
        quiet=True,
    )


if __name__ == "__main__":
    main()
