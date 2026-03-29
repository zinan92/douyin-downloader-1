<div align="center">

# Douyin Downloader

**批量下载抖音视频并自动转录、归档、生成结构化摘要 -- 从内容采集到文本分析的完整 pipeline**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Version 2.0.0](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/zinan92/douyin-downloader-1)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests 167](https://img.shields.io/badge/tests-167-brightgreen.svg)](tests/)

</div>

---

```
in  抖音 URL（视频/博主/合集/音乐/收藏夹）或本地媒体文件路径
out 去水印视频 + 转录文本(.txt/.json) + Markdown 归档(.md) + 结构化分析摘要(_analysis.json)

fail Cookie 过期或缺失          → 下载失败，提示重新获取 Cookie
fail 抖音风控触发分页限制        → 自动弹出浏览器让用户手动验证（browser_fallback）
fail OpenAI API key 无效/余额不足 → 转录失败，建议切换到 local provider
fail 本地 Whisper 未安装         → 转录失败，提示安装 mlx-whisper 或 openai-whisper
fail 视频 URL 无法解析           → 跳过该条目，继续处理队列中下一条
fail 网络超时/服务端 5xx         → 指数退避重试（1s → 2s → 5s），最多 3 次
```

Adapters: OpenAI API, mlx-whisper (Apple Silicon), openai-whisper (CPU)

## 示例输出

**CLI 运行效果：**

```
$ python3 run.py -c config.yml -u "https://www.douyin.com/video/7604129988555574538"

  Douyin Downloader v2.0.0
  ========================

  [1/1] 解析链接... ✓ 视频类型
  [1/1] 下载视频 (无水印)... ██████████████████████████████ 100% 12.4MB
  [1/1] 下载封面... ✓
  [1/1] 下载音乐... ✓
  [1/1] 保存元数据 JSON... ✓
  [1/1] 转录中 (provider: openai_api)... ✓ 2m34s 音频 → 1,247 字
  [1/1] 生成 Markdown 归档... ✓
  [1/1] 生成分析摘要... ✓

  完成! 已保存到 ./Downloaded/某博主_7604129988555574538/
```

**输出文件结构：**

```
Downloaded/某博主_7604129988555574538/
├── 视频标题.mp4                    # 去水印视频
├── 视频标题_cover.jpg              # 封面
├── 视频标题_music.mp3              # 背景音乐
├── 视频标题_data.json              # 抖音元数据
├── 视频标题.transcript.txt         # 格式化转录文本
├── 视频标题.transcript.json        # 原始转录 JSON
├── 视频标题.md                     # Markdown 归档
└── 视频标题_analysis.json          # 结构化分析摘要
```

**分析摘要示例（_analysis.json）：**

```json
{
  "title": "视频标题",
  "duration_seconds": 154,
  "word_count": 1247,
  "language": "zh",
  "topics": ["投资", "理财", "基金"],
  "summary": "视频讲解了基金定投的三大核心策略...",
  "key_points": [
    "定投频率建议每周一次",
    "选择宽基指数降低风险",
    "止盈不止损的操作原则"
  ]
}
```

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
# 克隆 + 安装
git clone https://github.com/zinan92/douyin-downloader-1.git
cd douyin-downloader-1
pip install -r requirements.txt

# 配置
cp config.example.yml config.yml
# 编辑 config.yml，填入 cookies 和目标链接

# 获取 Cookie（推荐自动方式）
pip install playwright && python -m playwright install chromium
python -m tools.cookie_fetcher --config config.yml

# 运行
python run.py -c config.yml
```

**本地视频（不需要抖音 Cookie）：**

```bash
python run.py -c config.yml -u /path/to/video.mp4
```

## 功能一览

| 功能 | 说明 | 状态 |
|------|------|------|
| 单视频下载 | `/video/{id}` 链接，自动去水印 | ✅ |
| 图文笔记下载 | `/note/{id}`、`/gallery/{id}` | ✅ |
| 合集下载 | `/collection/{id}`、`/mix/{id}` | ✅ |
| 音乐下载 | `/music/{id}` | ✅ |
| 博主批量下载 | `/user/{sec_uid}` + mode 配置 | ✅ |
| 收藏夹下载 | 登录态 `collect` / `collectmix` | ✅ |
| 短链解析 | `https://v.douyin.com/...` 自动跳转 | ✅ |
| 本地文件输入 | `.mp4/.mov/.m4v/.mp3/.wav/.m4a/.aac` | ✅ |
| 本地目录批量 | 自动扫描目录下所有媒体文件 | ✅ |
| OpenAI 转录 | `gpt-4o-mini-transcribe` 等 API | ✅ |
| 本地 Whisper 转录 | mlx-whisper (Apple Silicon) + CLI 回退 | ✅ |
| Markdown 归档 | 每视频生成带元数据的 `.md` | ✅ |
| JSON 分析摘要 | 结构化 `_analysis.json` | ✅ |
| 并发下载 | 可配置线程数，默认 5 | ✅ |
| 指数退避重试 | 1s → 2s → 5s，最多 3 次 | ✅ |
| SQLite 去重 | 数据库 + 本地文件双重校验 | ✅ |
| 增量下载 | `increase` 模式，只下新内容 | ✅ |
| 时间过滤 | `start_time` / `end_time` | ✅ |
| 浏览器兜底 | 风控分页时自动弹浏览器 | ✅ |
| Docker 部署 | Dockerfile 已包含 | ✅ |

## 三种输入模式

**抖音链接：**
```yaml
link:
  - https://www.douyin.com/video/7604129988555574538
```

**博主主页（批量）：**
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

**本地文件：**
```yaml
link:
  - /path/to/video.mp4           # 单文件
  - /path/to/video_directory/    # 整个目录
transcript:
  enabled: true
  provider: local
  local_model: small
```

## 转录 Provider

| Provider | 配置值 | 说明 |
|----------|--------|------|
| OpenAI API | `openai_api` | OpenAI 兼容 API（默认） |
| 本地 Whisper | `local` | mlx-whisper (Apple Silicon) + whisper CLI 回退 |
| 自动 | `auto` | 先试本地，失败走 API |

```bash
# Apple Silicon 推荐（快 5-10x）
pip install mlx-whisper

# CPU 通用版
pip install openai-whisper
```

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
├── tests/                        # 167 个测试
├── config.example.yml            # 配置模板
├── run.py                        # 入口脚本
└── pyproject.toml                # 项目元数据
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
| `OPENAI_API_KEY` | OpenAI 转录 API key（`openai_api` provider 时） | 条件必填 |
| `DOUYIN_COOKIE` | Cookie 字符串（替代 config 中的 cookies 节） | 否 |
| `DOUYIN_PROXY` | 代理地址 | 否 |

## For AI Agents

### Capability Contract

```yaml
name: douyin-downloader
version: "2.0.0"
capability: "批量下载抖音视频并转录归档为结构化文本"

input:
  - type: douyin_url
    formats: ["/video/{id}", "/user/{sec_uid}", "/collection/{id}", "/music/{id}", "v.douyin.com/xxx"]
  - type: local_file
    formats: [".mp4", ".mov", ".m4v", ".mp3", ".wav", ".m4a", ".aac"]
  - type: local_directory
    description: "目录下所有媒体文件"

output:
  per_item:
    - "{name}.mp4"                # 去水印视频
    - "{name}_cover.jpg"          # 封面
    - "{name}_music.mp3"          # 背景音乐
    - "{name}_data.json"          # 抖音元数据
    - "{name}.transcript.txt"     # 格式化转录文本
    - "{name}.transcript.json"    # 原始转录 JSON
    - "{name}.md"                 # Markdown 归档
    - "{name}_analysis.json"      # 结构化分析摘要
  global:
    - "download_manifest.jsonl"   # 下载清单
    - "dy_downloader.db"          # SQLite 去重数据库

failure_modes:
  - condition: "cookie_expired"
    behavior: "download fails, logs error"
    recovery: "re-run tools.cookie_fetcher"
  - condition: "rate_limited"
    behavior: "browser popup for manual verification"
    recovery: "complete CAPTCHA in browser"
  - condition: "api_key_invalid"
    behavior: "transcript fails, video still saved"
    recovery: "set valid OPENAI_API_KEY or switch to local provider"
  - condition: "whisper_not_installed"
    behavior: "transcript fails"
    recovery: "pip install mlx-whisper or openai-whisper"

cli:
  command: "python run.py"
  args:
    - name: "-u / --url"
      type: string
      description: "抖音 URL 或本地文件路径"
    - name: "-c / --config"
      type: string
      default: "config.yml"
      description: "配置文件路径"
    - name: "-p / --path"
      type: string
      description: "下载输出目录"
    - name: "-t / --thread"
      type: integer
      description: "并发下载数"
  flags:
    - name: "-v / --verbose"
      type: boolean
      description: "详细日志"

health_check: "python -c 'from core import URLParser; print(\"ok\")'"
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
