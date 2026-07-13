#!/usr/bin/env python3
"""全平台视频提取器 - Android 版 (Kivy)

在手机上运行的视频下载器，共享 desktop 版的核心引擎。
"""

import os
import sys
import threading
import json

# 确保能找到 video_downloader 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.clipboard import Clipboard

from video_downloader import VideoExtractor, detect_platform
from video_downloader.formats import get_quality_labels, get_format_str_by_label
from video_downloader.utils import (
    format_bytes,
    format_speed,
    format_eta,
    get_default_download_dir,
    friendly_error,
)

# Android storage
if platform == "android":
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    DEFAULT_DOWNLOAD_DIR = os.path.join(primary_external_storage_path(), "Download", "视频提取器")
else:
    DEFAULT_DOWNLOAD_DIR = get_default_download_dir()


class VideoDownloaderApp(App):
    """Kivy 主应用"""

    def build(self):
        self.title = "视频提取器"
        self.extractor = None
        self.downloading = False

        if platform == "android":
            request_permissions([
                Permission.INTERNET,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ])

        return MainScreen()


class MainScreen(BoxLayout):
    """主界面"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [15, 15, 15, 15]
        self.spacing = 10

        # ── 标题 ──
        title = Label(
            text="🎬 全平台视频提取器",
            font_size="20sp",
            bold=True,
            size_hint_y=None,
            height=50,
            color=(0.33, 0.71, 0.94, 1),  # #89b4fa
        )
        self.add_widget(title)

        subtitle = Label(
            text="B站 | 抖音 | YouTube | 小红书 | 快手 | 微博 | 西瓜视频",
            font_size="11sp",
            size_hint_y=None,
            height=30,
            color=(0.5, 0.5, 0.5, 1),
        )
        self.add_widget(subtitle)

        # ── URL 输入 ──
        self.add_widget(Label(
            text="🔗 视频链接",
            font_size="14sp",
            size_hint_y=None,
            height=25,
            halign="left",
        ))

        url_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=45, spacing=8)
        self.url_input = TextInput(
            hint_text="粘贴视频链接到这里...",
            font_size="14sp",
            multiline=False,
        )
        url_row.add_widget(self.url_input)

        add_btn = Button(
            text="添加",
            size_hint_x=None,
            width=70,
            background_color=(0.33, 0.71, 0.94, 1),
        )
        add_btn.bind(on_press=self._add_url)
        url_row.add_widget(add_btn)

        paste_btn = Button(
            text="粘贴",
            size_hint_x=None,
            width=70,
            background_color=(0.3, 0.3, 0.4, 1),
        )
        paste_btn.bind(on_press=self._paste)
        url_row.add_widget(paste_btn)

        self.add_widget(url_row)

        # ── 下载列表 ──
        self.add_widget(Label(
            text="📝 下载列表",
            font_size="14sp",
            size_hint_y=None,
            height=25,
        ))

        self.list_scroll = ScrollView(size_hint=(1, 0.45))
        self.list_layout = GridLayout(cols=1, size_hint_y=None, spacing=3)
        self.list_layout.bind(minimum_height=self.list_layout.setter("height"))
        self.list_scroll.add_widget(self.list_layout)
        self.add_widget(self.list_scroll)
        self._url_items = []  # [(url, platform_name, status_label, progress_bar)]

        # ── 设置 ──
        settings = GridLayout(cols=2, size_hint_y=None, height=80, spacing=[10, 5])

        settings.add_widget(Label(text="清晰度:", font_size="13sp"))
        self.quality_spinner = Spinner(
            text=get_quality_labels()[0],
            values=get_quality_labels(),
            font_size="12sp",
        )
        settings.add_widget(self.quality_spinner)

        settings.add_widget(Label(text="仅音频:", font_size="13sp"))
        audio_row = BoxLayout(size_hint_x=None, width=50)
        self.audio_check = CheckBox(active=False)
        audio_row.add_widget(self.audio_check)
        settings.add_widget(audio_row)

        self.add_widget(settings)

        # ── 操作按钮 ──
        btn_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=10)

        self.dl_btn = Button(
            text="⬇ 开始下载",
            font_size="16sp",
            background_color=(0.33, 0.71, 0.94, 1),
        )
        self.dl_btn.bind(on_press=self._start_download)
        btn_row.add_widget(self.dl_btn)

        clear_btn = Button(
            text="🗑 清空",
            size_hint_x=None,
            width=80,
            background_color=(0.3, 0.3, 0.4, 1),
        )
        clear_btn.bind(on_press=self._clear)
        btn_row.add_widget(clear_btn)

        self.add_widget(btn_row)

        # ── 全局进度 ──
        self.total_progress = ProgressBar(max=100, value=0, size_hint_y=None, height=8)
        self.add_widget(self.total_progress)

        self.status_label = Label(
            text="就绪 - 粘贴链接开始下载",
            font_size="12sp",
            size_hint_y=None,
            height=25,
            color=(0.6, 0.6, 0.6, 1),
        )
        self.add_widget(self.status_label)

    # ── 事件 ──

    def _add_url(self, instance):
        url = self.url_input.text.strip()
        if not url:
            return

        p = detect_platform(url)
        platform_name = f"{p.icon} {p.name}" if p else "❓ 未知"

        # 创建列表项
        item_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=36, spacing=5)
        status_lbl = Label(text="⏳", size_hint_x=None, width=30, font_size="14sp")
        url_lbl = Label(
            text=f"[{platform_name}] {url[:50]}...",
            font_size="11sp",
            halign="left",
            shorten=True,
        )
        prog_bar = ProgressBar(max=100, value=0, size_hint_x=None, width=100)

        item_box.add_widget(status_lbl)
        item_box.add_widget(url_lbl)
        item_box.add_widget(prog_bar)

        self.list_layout.add_widget(item_box)
        self._url_items.append({
            "url": url,
            "platform": platform_name,
            "status_label": status_lbl,
            "progress_bar": prog_bar,
            "box": item_box,
        })

        self.url_input.text = ""
        self.status_label.text = f"已添加 {len(self._url_items)} 个链接"

    def _paste(self, instance):
        text = Clipboard.paste()
        if text:
            self.url_input.text = text

    def _clear(self, instance):
        if hasattr(App.get_running_app(), 'downloading') and App.get_running_app().downloading:
            return
        self.list_layout.clear_widgets()
        self._url_items.clear()
        self.status_label.text = "列表已清空"

    def _start_download(self, instance):
        pending = [
            item for item in self._url_items
            if item["status_label"].text in ("⏳", "❌")
        ]
        if not pending:
            return

        app = App.get_running_app()
        app.downloading = True
        self.dl_btn.disabled = True
        self.status_label.text = f"开始下载 {len(pending)} 个视频..."

        thread = threading.Thread(target=self._download_all, args=(pending,), daemon=True)
        thread.start()

    def _download_all(self, pending):
        quality_label = self.quality_spinner.text
        audio_only = self.audio_check.active

        # 初始化引擎
        app = App.get_running_app()
        if app.extractor is None:
            app.extractor = VideoExtractor(
                output_dir=DEFAULT_DOWNLOAD_DIR,
            )

        for item in pending:
            if not app.downloading:
                break

            # 在主线程更新UI
            def set_status(status, progress=0):
                Clock.schedule_once(lambda dt: self._update_item_ui(item, status, progress))

            set_status("⬇", 0)

            try:
                def progress_cb(prog):
                    if prog.status == "downloading":
                        Clock.schedule_once(
                            lambda dt, p=prog: self._update_progress(item, p), 0
                        )

                result = app.extractor.download(
                    url=item["url"],
                    quality_label=quality_label,
                    progress_callback=progress_cb,
                    audio_only=audio_only,
                )

                if result.success:
                    set_status("✅", 100)
                else:
                    set_status("❌", 0)
                    Clock.schedule_once(
                        lambda dt, e=result.error: self._show_error(e), 0
                    )

            except Exception as e:
                set_status("❌", 0)
                Clock.schedule_once(
                    lambda dt, e=e: self._show_error(str(e)), 0
                )

        Clock.schedule_once(lambda dt: self._download_done())

    def _update_item_ui(self, item, status, progress):
        item["status_label"].text = status
        item["progress_bar"].value = progress

    def _update_progress(self, item, prog):
        item["status_label"].text = f"⬇ {prog.percent:.0f}%"
        item["progress_bar"].value = prog.percent

        speed = format_speed(prog.speed_bytes)
        eta = format_eta(prog.eta_seconds)
        self.status_label.text = f"下载中... {speed}  剩余 {eta}"

    def _show_error(self, msg):
        popup = Popup(
            title="下载失败",
            content=Label(text=friendly_error(Exception(msg)) if not isinstance(msg, str) else msg[:200]),
            size_hint=(0.8, 0.3),
        )
        popup.open()

    def _download_done(self):
        app = App.get_running_app()
        app.downloading = False
        self.dl_btn.disabled = False
        self.total_progress.value = 0
        self.status_label.text = "下载完成 ✅"


if __name__ == "__main__":
    VideoDownloaderApp().run()
