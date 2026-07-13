#!/usr/bin/env python3
"""全平台视频提取器 - 桌面版 (原生 tkinter GUI)"""

import os
import sys
import re
import queue
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from video_downloader import VideoExtractor, detect_platform
from video_downloader.formats import get_quality_labels
from video_downloader.utils import format_bytes, format_speed, format_eta, get_default_download_dir


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("全平台视频提取器")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)
        self.root.configure(bg="#1e1e2e")

        # 状态
        self.queue: list[dict] = []  # {url, platform_name, platform_icon, status}
        self.downloading = False
        self.cancel_flag = False
        self.update_queue = queue.Queue()

        # 引擎（懒加载）
        self.extractor: VideoExtractor = None

        self._setup_style()
        self._build_ui()
        self._start_polling()

    # ── 样式 ──────────────────────────────────────

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        BG = "#1e1e2e"
        FG = "#cdd6f4"
        ACCENT = "#89b4fa"
        BTN_BG = "#313244"
        RED = "#f38ba8"
        GREEN = "#a6e3a1"

        style.configure(".", background=BG, foreground=FG, fieldbackground=BTN_BG)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 18, "bold"), foreground=ACCENT)
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei UI", 9), foreground="#6c7086")
        style.configure("TButton", background=BTN_BG, foreground=FG, font=("Microsoft YaHei UI", 10))
        style.configure("Accent.TButton", background=ACCENT, foreground="#1e1e2e", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Danger.TButton", background=RED, foreground="#1e1e2e")
        style.configure("TEntry", fieldbackground="#313244", foreground=FG, font=("Microsoft YaHei UI", 10))
        style.configure("TCombobox", fieldbackground="#313244", foreground=FG, font=("Microsoft YaHei UI", 10))
        style.configure("TProgressbar", troughcolor="#313244", background=GREEN)
        style.configure("Treeview", background="#181825", foreground=FG, fieldbackground="#181825", font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", background=BTN_BG, foreground=FG, font=("Microsoft YaHei UI", 9, "bold"))
        style.map("TCombobox", fieldbackground=[("readonly", "#313244")], foreground=[("readonly", FG)])

        # 平台标签颜色
        self.platform_colors = {
            "bilibili": "#00a1d6",
            "douyin": "#fe2c55",
            "youtube": "#ff0000",
            "xiaohongshu": "#ff2442",
            "kuaishou": "#ff4906",
            "weibo": "#e6162d",
            "xigua": "#f0412d",
        }

    # ── UI构建 ─────────────────────────────────────

    def _build_ui(self):
        # 标题
        header = ttk.Frame(self.root)
        header.pack(pady=(20, 5))
        ttk.Label(header, text="🎬 全平台视频提取器", style="Title.TLabel").pack()
        ttk.Label(header, text="支持 B站 | 抖音 | YouTube | 小红书 | 快手 | 微博 | 西瓜视频  ·  免费开源",
                  style="Subtitle.TLabel").pack()

        # 平台标签行
        badge_frame = ttk.Frame(self.root)
        badge_frame.pack(pady=5)
        platforms = [("B站", "#00a1d6"), ("抖音", "#fe2c55"), ("YouTube", "#ff0000"),
                     ("小红书", "#ff2442"), ("快手", "#ff4906"), ("微博", "#e6162d"), ("西瓜视频", "#f0412d")]
        for name, color in platforms:
            b = tk.Label(badge_frame, text=name, fg=color, bg="#313244",
                         font=("Microsoft YaHei UI", 9), padx=10, pady=2,
                         relief="flat", borderwidth=0)
            b.pack(side="left", padx=3)

        # ── URL输入区 ──
        url_frame = ttk.Frame(self.root)
        url_frame.pack(fill="x", padx=20, pady=(15, 5))

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Microsoft YaHei UI", 11))
        url_entry.pack(side="left", fill="x", expand=True, ipady=4)
        url_entry.bind("<Return>", lambda e: self._add_url())

        add_btn = ttk.Button(url_frame, text="➕ 添加", command=self._add_url, width=10)
        add_btn.pack(side="left", padx=5)

        paste_btn = ttk.Button(url_frame, text="📋 批量粘贴", command=self._paste_urls, width=12)
        paste_btn.pack(side="left")

        # ── 下载队列 ──
        list_frame = ttk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        columns = ("status", "title", "platform", "progress")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        self.tree.heading("status", text="状态")
        self.tree.heading("title", text="视频标题")
        self.tree.heading("platform", text="平台")
        self.tree.heading("progress", text="进度")
        self.tree.column("status", width=60, anchor="center")
        self.tree.column("title", width=380)
        self.tree.column("platform", width=100, anchor="center")
        self.tree.column("progress", width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 右键菜单
        self.tree_menu = tk.Menu(self.root, tearoff=0, bg="#313244", fg="#cdd6f4",
                                 font=("Microsoft YaHei UI", 9))
        self.tree_menu.add_command(label="🗑 移除选中", command=self._remove_selected)
        self.tree_menu.add_command(label="🗑 清空已完成", command=self._clear_completed)
        self.tree.bind("<Button-3>", self._show_tree_menu)

        # ── 设置区 ──
        settings_frame = ttk.Frame(self.root)
        settings_frame.pack(fill="x", padx=20, pady=5)

        # 清晰度
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.pack(side="left", padx=(0, 15))
        ttk.Label(quality_frame, text="清晰度").pack(anchor="w")
        self.quality_var = tk.StringVar(value=get_quality_labels()[0])
        quality_box = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                   values=get_quality_labels(), state="readonly", width=24)
        quality_box.pack(ipady=3)

        # 输出目录
        dir_frame = ttk.Frame(settings_frame)
        dir_frame.pack(side="left", padx=(0, 15))
        ttk.Label(dir_frame, text="保存目录").pack(anchor="w")
        dir_row = ttk.Frame(dir_frame)
        dir_row.pack()
        self.dir_var = tk.StringVar(value=get_default_download_dir())
        dir_entry = ttk.Entry(dir_row, textvariable=self.dir_var, width=30)
        dir_entry.pack(side="left", ipady=3)
        ttk.Button(dir_row, text="📁", command=self._pick_dir, width=4).pack(side="left", padx=3)

        # Cookie + 代理
        extra_frame = ttk.Frame(settings_frame)
        extra_frame.pack(side="left", padx=(0, 15))
        ttk.Label(extra_frame, text="浏览器Cookie").pack(anchor="w")
        self.cookie_var = tk.StringVar(value="")
        cookie_box = ttk.Combobox(extra_frame, textvariable=self.cookie_var,
                                  values=["", "chrome", "firefox", "edge", "brave"],
                                  state="readonly", width=14)
        cookie_box.pack(ipady=3)

        proxy_frame = ttk.Frame(settings_frame)
        proxy_frame.pack(side="left")
        ttk.Label(proxy_frame, text="代理").pack(anchor="w")
        self.proxy_var = tk.StringVar()
        proxy_entry = ttk.Entry(proxy_frame, textvariable=self.proxy_var, width=16)
        proxy_entry.pack(ipady=3)

        # ── 操作按钮 ──
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20, pady=(10, 5))

        self.dl_btn = ttk.Button(btn_frame, text="⬇ 开始下载", command=self._start_download,
                                 style="Accent.TButton")
        self.dl_btn.pack(side="left", ipadx=20, ipady=5)

        ttk.Button(btn_frame, text="🗑 清空列表", command=self._clear_all).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="⏹ 取消下载", command=self._cancel, style="Danger.TButton").pack(side="left")

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, mode="determinate")
        self.progress_bar.pack(fill="x", padx=20, pady=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪 - 粘贴视频链接开始下载")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken",
                               font=("Microsoft YaHei UI", 9), padding=(10, 5))
        status_bar.pack(fill="x", side="bottom")

        # 关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 事件处理 ──────────────────────────────────

    def _add_url(self):
        url = self.url_var.get().strip()
        if not url:
            return
        # 去重
        for item in self.queue:
            if item["url"] == url:
                messagebox.showinfo("提示", "链接已存在")
                self.url_var.set("")
                return

        p = detect_platform(url)
        platform_name = f"{p.icon} {p.name}" if p else "❓ 未知"
        platform_key = p.key if p else "unknown"
        color = self.platform_colors.get(platform_key, "#6c7086")

        item = {"url": url, "platform_name": platform_name, "platform_key": platform_key,
                "color": color, "status": "排队中", "title": "", "progress_text": ""}
        self.queue.append(item)
        self._refresh_tree()
        self.url_var.set("")
        self.status_var.set(f"已添加 {len(self.queue)} 个链接")

    def _paste_urls(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("提示", "剪贴板为空")
            return

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        added = 0
        existing = {item["url"] for item in self.queue}
        for line in lines:
            if line not in existing:
                p = detect_platform(line)
                platform_name = f"{p.icon} {p.name}" if p else "❓ 未知"
                platform_key = p.key if p else "unknown"
                color = self.platform_colors.get(platform_key, "#6c7086")
                self.queue.append({
                    "url": line, "platform_name": platform_name, "platform_key": platform_key,
                    "color": color, "status": "排队中", "title": "", "progress_text": ""
                })
                existing.add(line)
                added += 1

        self._refresh_tree()
        self.status_var.set(f"批量添加 {added} 个链接（共 {len(self.queue)} 个）")

    def _pick_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.dir_var.set(path)

    def _show_tree_menu(self, event):
        sel = self.tree.selection()
        if sel:
            self.tree_menu.post(event.x_root, event.y_root)

    def _remove_selected(self):
        sel = self.tree.selection()
        if sel:
            indices = sorted([int(self.tree.item(s)["iid"]) for s in sel], reverse=True)
            for i in indices:
                if 0 <= i < len(self.queue):
                    self.queue.pop(i)
            self._refresh_tree()

    def _clear_completed(self):
        self.queue = [item for item in self.queue if item["status"] not in ("✅ 完成", "❌ 失败")]
        self._refresh_tree()

    def _clear_all(self):
        if self.downloading:
            messagebox.showwarning("提示", "下载中无法清空，请先取消")
            return
        self.queue.clear()
        self._refresh_tree()
        self.status_var.set("列表已清空")

    def _cancel(self):
        if self.downloading:
            self.cancel_flag = True
            self.status_var.set("⏹ 正在取消...")

    def _on_close(self):
        if self.downloading:
            if messagebox.askyesno("确认", "正在下载中，确定退出吗？"):
                self.cancel_flag = True
                self.root.after(500, self.root.destroy)
        else:
            self.root.destroy()

    # ── 列表刷新 ──────────────────────────────────

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, item in enumerate(self.queue):
            values = (item["status"], item["title"] or item["url"][:60],
                      item["platform_name"], item.get("progress_text", ""))
            self.tree.insert("", "end", iid=str(i), values=values)

    def _update_item(self, index: int, **kwargs):
        if 0 <= index < len(self.queue):
            self.queue[index].update(kwargs)
            self._refresh_tree()

    # ── 下载引擎 ──────────────────────────────────

    def _get_extractor(self):
        if self.extractor is None:
            out = self.dir_var.get() or get_default_download_dir()
            cookie = self.cookie_var.get().strip()
            proxy = self.proxy_var.get().strip()
            self.extractor = VideoExtractor(
                output_dir=out,
                use_browser_cookies=cookie if cookie else None,
                proxy=proxy if proxy else None,
            )
        return self.extractor

    def _start_download(self):
        if self.downloading:
            return
        pending = [
            (i, item) for i, item in enumerate(self.queue)
            if item["status"] in ("排队中", "❌ 失败")
        ]
        if not pending:
            messagebox.showinfo("提示", "没有待下载的链接")
            return

        self.downloading = True
        self.cancel_flag = False
        self.dl_btn.configure(state="disabled")
        self.status_var.set(f"开始下载 {len(pending)} 个视频...")

        thread = threading.Thread(target=self._download_thread, args=(pending,), daemon=True)
        thread.start()

    def _download_thread(self, pending: list):
        extractor = self._get_extractor()

        for i, item in pending:
            if self.cancel_flag:
                break

            self._update_item(i, status="⬇ 下载中", progress_text="0%")
            self.update_queue.put(("progress_bar", 0))

            # 进度回调（线程安全）
            def make_progress(idx):
                def cb(prog):
                    if prog.status == "downloading" and prog.percent > 0:
                        text = f"{prog.percent:.0f}%  {format_speed(prog.speed_bytes)}  {format_eta(prog.eta_seconds)}"
                        self.update_queue.put(("update_item", idx, {
                            "status": f"⬇ {prog.percent:.0f}%",
                            "progress_text": text,
                            "title": prog.title[:50] if prog.title else "",
                        }))
                        self.update_queue.put(("progress_bar", prog.percent))
                    elif prog.status == "done":
                        self.update_queue.put(("progress_bar", 100))
                return cb

            result = extractor.download(
                url=item["url"],
                quality_label=self.quality_var.get(),
                progress_callback=make_progress(i),
            )

            if result.success:
                self.update_queue.put(("update_item", i, {
                    "status": "✅ 完成",
                    "title": result.title[:50],
                    "progress_text": f"{format_bytes(result.file_size)}  {result.elapsed_seconds:.1f}秒",
                }))
                self.update_queue.put(("status", f"✅ {result.title[:30]} 下载完成"))
            else:
                self.update_queue.put(("update_item", i, {
                    "status": "❌ 失败",
                    "progress_text": result.error[:80],
                }))
                self.update_queue.put(("status", f"❌ 下载失败: {result.error[:60]}"))

        self.update_queue.put(("done", None))

    # ── UI轮询 ────────────────────────────────────

    def _start_polling(self):
        """定期检查 update_queue，在主线程更新UI"""
        try:
            while True:
                msg = self.update_queue.get_nowait()
                action = msg[0]
                if action == "update_item":
                    self._update_item(msg[1], **(msg[2] or {}))
                elif action == "progress_bar":
                    self.progress_var.set(msg[1] or 0)
                elif action == "status":
                    self.status_var.set(msg[1])
                elif action == "done":
                    self.downloading = False
                    self.cancel_flag = False
                    self.dl_btn.configure(state="normal")
                    self.progress_var.set(0)
                elif action == "all_done":
                    pass
        except queue.Empty:
            pass
        self.root.after(200, self._start_polling)


def main():
    app = App()
    app.root.mainloop()


if __name__ == "__main__":
    main()
