<div align="center">

# douyin-downloader

**抖音全量内容下载 + 语音转录 + 结构化归档，一条 pipeline 搞定**

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-171%20passed-brightgreen.svg)](#测试)

</div>

---

## 痛点

想批量保存某个抖音博主的所有视频？想把视频内容转成文字方便检索？现有工具要么只能下载不能转录，要么转录完只给你一堆散落的 `.txt`，没有结构化元数据、没有可读归档、没法接入后续分析 pipeline。

## 解决方案

一个工具覆盖完整链路：**下载 → 转录 → 归档 → 分析**。支持抖音链接、博主主页批量、本地视频文件三种输入。转录支持 OpenAI API 和本地 Whisper 双模式。每个视频自动产出四份文件：原始转录、格式化文本、Markdown 归档、结构化 JSON 摘要。全程 SQLite 去重 + 断点续传。

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  输入解析     │────▶│  下载引擎     │────▶│  转录 Provider │
│  URL / 本地   │     │  并发 + 重试  │     │  OpenAI / 本地 │
└─────────────┘     └─────────────┘     └──────┬───────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                    ┌───────────┐       ┌───────────┐       ┌───────────┐
                    │ .txt/.json │       │ .md 归档   │       │ _analysis │
                    │ 原始转录    │       │ 格式化文档  │       │ JSON 摘要  │
                    └───────────┘       └───────────┘       └───────────┘
                                               │
                                               ▼
                                        ┌───────────┐
                                        │  SQLite DB │
                                        │  去重 + 记录 │
                                        └───────────┘
```

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/zinan92/douyin-downloader-1.git
cd douyin-downloader-1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置
cp config.example.yml config.yml
# 编辑 config.yml，填入 cookies 和目标链接

# 4. 获取 cookies（推荐自动方式）
pip install playwright && python -m playwright install chromium
python -m tools.cookie_fetcher --config config.yml

# 5. 运行
python run.py -c config.yml
```

### 本地视频（不需要抖音）

```bash
# 直接转录本地文件，无需 cookies
python run.py -c config.yml -u /path/to/video.mp4
```

## 功能一览

| 功能 | 说明 | 状态 |
|------|------|------|
| 单视频下载 | `/video/{id}` 链接，自动去水印 | 已完成 |
| 图文笔记下载 | `/note/{id}`、`/gallery/{id}` | 已完成 |
| 合集下载 | `/collection/{id}`、`/mix/{id}` | 已完成 |
| 音乐下载 | `/music/{id}` | 已完成 |
| 博主批量下载 | `/user/{sec_uid}` + mode 配置 | 已完成 |
| 收藏夹下载 | 登录态下的 `collect` / `collectmix` | 已完成 |
| 短链解析 | `https://v.douyin.com/...` 自动跳转 | 已完成 |
| 本地文件输入 | `.mp4/.mov/.m4v/.mp3/.wav/.m4a/.aac` | 已完成 |
| 本地目录批量 | 指定目录，自动扫描所有媒体文件 | 已完成 |
| OpenAI 转录 | `gpt-4o-mini-transcribe` 等 API | 已完成 |
| 本地 Whisper 转录 | mlx-whisper (Apple Silicon) + CLI 回退 | 已完成 |
| Markdown 归档 | 每视频生成带元数据的 `.md` | 已完成 |
| JSON 分析摘要 | 结构化 `_analysis.json` | 已完成 |
| 并发下载 | 可配置线程数，默认 5 | 已完成 |
| 指数退避重试 | 1s → 2s → 5s | 已完成 |
| SQLite 去重 | 数据库 + 本地文件双重校验 | 已完成 |
| 增量下载 | `increase` 模式，只下新内容 | 已完成 |
| 时间过滤 | `start_time` / `end_time` | 已完成 |
| 浏览器兜底 | 风控分页时自动弹浏览器 | 已完成 |
| Docker 部署 | Dockerfile 已包含 | 已完成 |

## 三种输入模式

### 1. 抖音链接

```yaml
link:
  - https://www.douyin.com/video/7604129988555574538
```

### 2. 博主主页（批量）

```yaml
link:
  - https://www.douyin.com/user/MS4wLjABAAAAxxxx
mode:
  - post
  - like
number:
  post: 50
  like: 0    # 0 = 全部
```

### 3. 本地文件

```yaml
link:
  - /path/to/video.mp4           # 单文件
  - /path/to/video_directory/    # 整个目录

transcript:
  enabled: true
  provider: local
  local_model: small
```

## Pipeline: 转录 → 归档 → 分析

当 `transcript.enabled: true` 时，每个视频自动走完三阶段：

```
视频文件 ──▶ [转录] ──▶ [归档] ──▶ [分析]
              │          │          │
              ▼          ▼          ▼
          .txt/.json    .md    _analysis.json
```

### 转录 Provider

| Provider | 配置值 | 说明 |
|----------|--------|------|
| OpenAI API | `openai_api` | OpenAI 兼容 API（默认） |
| 本地 Whisper | `local` | mlx-whisper (Apple Silicon) + whisper CLI 回退 |
| 自动 | `auto` | 先试本地，失败走 API |

```bash
# Apple Silicon 推荐（快 5-10x）
pip install mlx-whisper

# 或 CPU 通用版
pip install openai-whisper
```

### 产出文件示例

转录开启后，每个视频产出：

| 文件 | 内容 |
|------|------|
| `xxx.transcript.txt` | 格式化纯文本（按句分段） |
| `xxx.transcript.json` | 原始转录 JSON |
| `xxx.md` | Markdown 归档（标题 + 元数据 + 正文） |
| `xxx_analysis.json` | 结构化摘要（标题、作者、标签、摘要） |

## 输出目录结构

```
workspace/
├── config.yml
├── dy_downloader.db
└── Downloaded/
    ├── download_manifest.jsonl
    └── 博主名/
        └── post/
            └── 2026-03-22_标题_aweme_id/
                ├── 2026-03-22_标题_aweme_id.mp4
                ├── ..._cover.jpg
                ├── ..._music.mp3
                ├── ..._data.json
                ├── ..._avatar.jpg
                ├── ....transcript.txt
                ├── ....transcript.json
                ├── ....md
                └── ..._analysis.json
```

## 配置

核心配置项（完整模板见 `config.example.yml`）：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `link` | 抖音 URL 列表或本地文件路径 | 必填 |
| `path` | 下载保存目录 | `./Downloaded/` |
| `mode` | 下载模式：`post`/`like`/`mix`/`music`/`collect`/`collectmix` | `[post]` |
| `thread` | 并发数 | `5` |
| `database` | 启用 SQLite 去重 | `true` |
| `transcript.enabled` | 启用转录 pipeline | `false` |
| `transcript.provider` | 转录引擎：`openai_api` / `local` / `auto` | `openai_api` |
| `transcript.local_model` | 本地 Whisper 模型大小 | `small` |
| `archive.enabled` | 生成 Markdown 归档 | `true` |
| `analysis.enabled` | 生成 JSON 分析摘要 | `true` |
| `proxy` | HTTP 代理 | 空 |
| `browser_fallback.enabled` | 风控时弹浏览器 | `true` |

环境变量：

| 变量 | 说明 | 必填 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI 转录 API key（使用 `openai_api` provider 时） | 条件必填 |
| `DOUYIN_COOKIE` | Cookie 字符串（替代 config 中的 cookies 节） | 否 |
| `DOUYIN_PROXY` | 代理地址 | 否 |

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.8+ | 核心运行时 |
| 异步 | aiohttp + aiofiles | 并发下载与文件 IO |
| 数据库 | aiosqlite (SQLite) | 去重、历史、转录任务记录 |
| 转录 | mlx-whisper / openai-whisper / OpenAI API | 语音转文字 |
| 签名 | ABogus + XBogus (gmssl) | 抖音 API 签名 |
| UI | Rich | 终端进度条 |
| 浏览器 | Playwright (可选) | Cookie 获取 + 风控兜底 |
| 配置 | PyYAML | YAML 配置加载 |

## 项目结构

```
douyin-downloader-1/
├── cli/                          # CLI 入口与进度显示
│   ├── main.py                   # 主入口，参数解析
│   ├── progress_display.py       # Rich 进度条
│   └── whisper_transcribe.py     # 独立 Whisper 批量转录工具
├── core/                         # 核心业务逻辑
│   ├── api_client.py             # 抖音 API 客户端（签名、分页）
│   ├── downloader_base.py        # 下载器基类（资产下载、去重）
│   ├── downloader_factory.py     # 下载器工厂
│   ├── video_downloader.py       # 单视频下载
│   ├── user_downloader.py        # 博主批量下载
│   ├── mix_downloader.py         # 合集下载
│   ├── music_downloader.py       # 音乐下载
│   ├── url_parser.py             # URL 类型解析（含本地文件检测）
│   ├── pipeline.py               # 统一 pipeline（本地文件入口）
│   ├── transcript_manager.py     # 转录编排（provider + 归档 + 分析）
│   ├── transcript_formatter.py   # 转录文本格式化（按句分段）
│   ├── archive_manager.py        # Markdown 归档输出
│   ├── analysis_manager.py       # JSON 分析摘要
│   ├── transcript_providers/     # 转录 provider 抽象层
│   │   ├── base.py               # TranscriptProvider ABC
│   │   ├── openai_provider.py    # OpenAI API provider
│   │   └── local_whisper_provider.py  # mlx-whisper + CLI 回退
│   └── user_modes/               # 博主下载模式策略
├── config/                       # 配置加载与默认值
├── storage/                      # 数据库 + 文件管理
├── auth/                         # Cookie 管理
├── control/                      # 队列、限速、重试
├── utils/                        # 工具函数（签名、校验、日志）
├── tools/                        # 辅助工具（Cookie 获取器）
├── tests/                        # 171 个测试
├── config.example.yml            # 配置模板
├── run.py                        # 入口脚本
└── pyproject.toml                # 项目元数据
```

## 测试

```bash
# 运行全部测试（171 个）
python3 -m pytest -q

# 只跑新增的 pipeline 测试
python3 -m pytest tests/test_pipeline.py tests/test_transcript_providers.py -v
```

## FAQ

**Q: 博主主页只能拉到 20 条？**
风控限制分页。确保 `browser_fallback.enabled: true` + `headless: false`，弹出浏览器后手动完成验证。

**Q: 转录文件没有生成？**
按顺序排查：`transcript.enabled` 是否为 `true` → 是否是视频（图文不转录）→ provider 依赖是否安装 → API key 是否有效。

**Q: 本地文件怎么用？**
`link` 里直接写文件路径或目录路径，支持 `.mp4/.mov/.m4v/.mp3/.wav/.m4a/.aac`。不需要 cookies。

**Q: Cookie 过期了？**
重新运行 `python -m tools.cookie_fetcher --config config.yml`。

**Q: 怎么强制重新下载？**
删本地文件 + 删数据库记录。只删数据库不够（程序扫文件名去重），只删文件会触发重下。

## For AI Agents

本节面向需要将此项目作为工具或依赖集成的 AI Agent。

### 结构化元数据

```yaml
name: douyin-downloader
description: "Douyin content pipeline: download, transcribe, archive, analyze"
version: "2.0.0"
cli_command: python run.py
cli_args:
  - name: -u / --url
    type: string
    required: false
    description: "Douyin URL, local file path, or local directory path"
  - name: -c / --config
    type: string
    required: false
    description: "Config file path (default: config.yml)"
  - name: -p / --path
    type: string
    required: false
    description: "Download output directory"
  - name: -t / --thread
    type: integer
    required: false
    description: "Concurrent download count"
cli_flags:
  - name: -v / --verbose
    type: boolean
    description: "Enable verbose logging"
install_command: "pip install -r requirements.txt"
start_command: "python run.py -c config.yml"
health_check: "python -c 'from core import URLParser; print(\"ok\")'"
dependencies:
  - aiohttp
  - aiofiles
  - aiosqlite
  - rich
  - pyyaml
  - gmssl
optional_dependencies:
  - mlx-whisper (Apple Silicon local transcription)
  - openai-whisper (CPU local transcription)
  - playwright (browser fallback + cookie fetcher)
capabilities:
  - "download Douyin videos without watermark"
  - "batch download all posts from a Douyin creator profile"
  - "transcribe video audio to text (OpenAI API or local Whisper)"
  - "generate formatted Markdown archive per video"
  - "generate structured JSON analysis summary per video"
  - "process local media files without Douyin API"
  - "deduplicate downloads via SQLite + local file scan"
input_format: "YAML config file or CLI args (URLs / local file paths)"
output_format: "Media files + .transcript.txt + .transcript.json + .md + _analysis.json"
```

### Agent 调用示例

```python
import subprocess
import json
from pathlib import Path

# 场景 1: 下载单个视频并转录
def download_and_transcribe(video_url: str, output_dir: str = "./Downloaded"):
    result = subprocess.run(
        ["python", "run.py", "-c", "config.yml", "-u", video_url, "-p", output_dir],
        capture_output=True, text=True, cwd="/path/to/douyin-downloader-1"
    )
    return result.returncode == 0

# 场景 2: 转录本地视频（不需要抖音 API）
def transcribe_local(video_path: str):
    result = subprocess.run(
        ["python", "run.py", "-c", "config.yml", "-u", video_path],
        capture_output=True, text=True, cwd="/path/to/douyin-downloader-1"
    )
    return result.returncode == 0

# 场景 3: 读取分析结果
def read_analysis(analysis_json_path: str) -> dict:
    return json.loads(Path(analysis_json_path).read_text(encoding="utf-8"))

# 场景 4: 直接调用 pipeline（Python API）
async def pipeline_api():
    from core.pipeline import process_local_file
    result = await process_local_file(
        Path("/path/to/video.mp4"),
        config={
            "transcript": {"provider": "local", "language_hint": "zh"},
            "archive": {"enabled": True},
            "analysis": {"enabled": True},
        },
        output_dir=Path("./output"),
    )
    # result: {"status": "success", "transcript_path": ..., "markdown_path": ..., "analysis_path": ...}
    return result
```

## 相关项目

| 项目 | 说明 | 链接 |
|------|------|------|
| douyin-downloader (原版) | 单文件 pipeline，专注转录 + Markdown 输出 | [zinan92/douyin-downloader](https://github.com/zinan92/douyin-downloader) |
| xiaohongshu-downloader | 小红书内容下载器 | 同系列工具 |

## Disclaimer

本项目仅供技术研究、学习和个人数据管理使用。请合法合规使用，不得侵犯他人隐私或版权。使用者自行承担一切风险和法律责任。

## License

MIT
