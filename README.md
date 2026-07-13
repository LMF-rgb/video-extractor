# 🎬 全平台视频提取器

免费、开源、永不收费的视频下载工具。支持国内外主流平台。

## ✨ 支持的平台

| 平台 | 需要Cookie | 说明 |
|------|-----------|------|
| 📺 B站 (B站) | 1080P+需要 | 支持 BV/av 链接和 b23 短链 |
| 🎵 抖音 | 部分需要 | 自动去水印，支持短链 |
| ▶️ YouTube | 年龄限制需要 | 自动合并最佳音视频流 |
| 📕 小红书 | 需要 | 自动区分图文/视频 |
| ⚡ 快手 | 不需要 | 自动去水印 |
| 📢 微博 | 需要 | 支持短链 t.cn |
| 🍉 西瓜视频 | 不需要 | 支持 ixigua 链接 |

## 🚀 快速开始

### 方式一：一键启动（推荐）
双击 `启动视频提取器.bat`

### 方式二：命令行
```bash
# 1. 安装依赖
pip install -r desktop/requirements.txt

# 2. 安装 FFmpeg（必须！）
# 下载: https://ffmpeg.org/download.html
# 或: winget install ffmpeg

# 3. 启动
python desktop/app.py
```

### 方式三：测试
```bash
python test_download.py
```

## 📖 使用说明

1. **打开软件** → 浏览器自动打开界面
2. **粘贴链接** → 支持 B站/抖音/YouTube/小红书等
3. **选择清晰度** → 最佳/1080P/720P/480P/仅音频
4. **点击下载** → 实时显示速度和进度
5. **完成！** → 视频保存到 `~/Videos/视频提取器/`

## 🍪 Cookie 设置（高清必备）

B站1080P、YouTube年龄限制、小红书等需要登录：

1. 用 Chrome/Edge 登录对应网站
2. 在软件中选择 `浏览器Cookie` → `chrome` / `edge`
3. 程序会自动读取浏览器的登录状态

## 🔧 常见问题

| 问题 | 解决 |
|------|------|
| B站只能下载720P | 设置浏览器Cookie，登录B站账号 |
| YouTube 提示登录 | 设置浏览器Cookie 或 使用代理 |
| 下载失败 403 | 换CDN节点或等几分钟重试 |
| "ffmpeg not found" | 安装 FFmpeg: `winget install ffmpeg` |
| 抖音链接无效 | 确保是完整链接（复制时选"复制链接"） |

## 📁 目录结构

```
003-video-extractor/
├── video_downloader/       # 共享核心引擎
│   ├── engine.py           # yt-dlp 下载封装
│   ├── platforms.py        # 平台识别配置
│   ├── formats.py          # 清晰度管理
│   └── utils.py            # 工具函数
├── desktop/                # 桌面版 (Gradio)
│   ├── app.py              # GUI 主程序
│   └── requirements.txt
├── android/                # 安卓版 (Kivy)
│   ├── main.py
│   └── buildozer.spec
├── test_download.py        # 测试脚本
└── 启动视频提取器.bat      # 一键启动
```

## 🛠 技术栈

- **下载引擎**: [yt-dlp](https://github.com/yt-dlp/yt-dlp) (MIT开源, 1700+网站)
- **桌面框架**: [Gradio](https://gradio.app) (Apache 2.0)
- **安卓框架**: [Kivy](https://kivy.org) (MIT)

## ⚠️ 免责声明

本工具仅供个人学习使用，请勿用于商业用途或大规模爬取。
下载视频请遵守各平台的服务条款和版权法规。

## 📝 License

MIT License - 自由使用、修改、分发
