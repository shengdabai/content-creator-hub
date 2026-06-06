# ✍️ Content Creator Hub

**English | [中文](#中文)**

[![Last commit](https://img.shields.io/github/last-commit/shengdabai/content-creator-hub)](https://github.com/shengdabai/content-creator-hub/commits)
[![Stars](https://img.shields.io/github/stars/shengdabai/content-creator-hub?style=social)](https://github.com/shengdabai/content-creator-hub/stargazers)
[![Follow @shengdabai](https://img.shields.io/github/followers/shengdabai?style=social)](https://github.com/shengdabai)

> A trio of AI-powered tools that take you from idea to published post — write, score, and ship content to X (Twitter) and YouTube without leaving your terminal.

## Why

Creating consistent content across X and YouTube means juggling drafting, style, scoring, posting, and video production. These tools collapse that workflow into three focused, self-contained agents — built and used in public by a Chinese-language teacher who automates his own publishing.

## What

A monorepo of three independent tools that share one philosophy: **AI does the heavy lifting, you stay in control.**

| Tool | What it does | Stack |
|------|--------------|-------|
| **x-content-mvp** | Web app that turns a URL/text/image into scored X drafts, with style learning | Python · FastAPI · OpenAI SDK |
| **x-poster** | Terminal agent that drafts and posts tweets & threads to X | Python · Anthropic SDK · X API v2 (tweepy) |
| **youtube-creator** | Terminal agent that scripts, composes, and uploads YouTube videos | Python · Anthropic SDK · edge-tts · ffmpeg · YouTube Data API v3 |

## ✨ Features

### x-content-mvp — X content creation web app
- **Insight Extractor** — pulls core claim, key points, evidence, novelty, audience value, and tweetable angles from any URL, text, or uploaded image
- **Style Studio** — imports your historical posts (textarea / txt / csv) and rebuilds a structured style profile
- **Draft Composer** — 5 post types (`hot_take`, `insight_post`, `thread`, `contrarian`, `personal_brand`) × 3 tones (`safe`, `sharp`, `bold`)
- **Draft Scoring** — rates `style_match`, `clarity`, `attention`, `novelty`, and `overall`
- **Draft Library** — browse and query every draft, persisted in SQLite
- **Works without an API key** — falls back to deterministic heuristics so the product is always usable

### x-poster — automated X posting agent
- AI-generated tweet content via a tool-using agent loop
- Direct posting of single tweets **and** threads to X via API v2 (tweepy)
- Local draft saving and a published-tweet log
- Read-back of your recent tweets

### youtube-creator — AI YouTube video agent
- AI-generated scripts driven by a tool-using agent loop
- Asset generation: `edge-tts` voiceover + auto SRT captions + background image
- Video composition with `ffmpeg` into a final MP4
- Upload to YouTube via Data API v3 with OAuth2

## 🧱 Tech stack

- **Language:** Python 3.9+
- **Web:** FastAPI · Uvicorn · Jinja2
- **AI:** OpenAI SDK · Anthropic SDK
- **Integrations:** X API v2 (tweepy) · YouTube Data API v3 · edge-tts · ffmpeg
- **Storage:** SQLite (local)

## 🚀 Quick start

Each tool is self-contained in its own directory. Pick the one you need.

### x-content-mvp (web app)
```bash
cd x-content-mvp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add OPENAI_API_KEY=YOUR_KEY_HERE
./start.sh                  # or: uvicorn app.main:app --reload --port 8000
# open http://127.0.0.1:8000
```

### x-poster (terminal agent)
```bash
cd x-poster
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic python-dotenv tweepy
cp .env.example .env        # add ANTHROPIC_API_KEY + X API v2 credentials
python3 x-poster.py
```

### youtube-creator (terminal agent)
```bash
cd youtube-creator
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic python-dotenv edge-tts \
  google-auth-oauthlib google-api-python-client
# requires ffmpeg on your PATH (brew install ffmpeg)
cp .env.example .env        # add ANTHROPIC_API_KEY + YouTube OAuth credentials
python3 youtube-creator.py
```

> 🔑 Keys live in per-tool `.env` files (gitignored). Use placeholders like `OPENAI_API_KEY=YOUR_KEY_HERE` — never commit real keys.

## 📖 Usage

**Environment variables** (each tool ships its own `.env.example`):

| Tool | Required variables |
|------|--------------------|
| x-content-mvp | `OPENAI_API_KEY` |
| x-poster | `ANTHROPIC_API_KEY`, `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` |
| youtube-creator | `ANTHROPIC_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` |

**x-content-mvp key endpoints:**
- `POST /api/sources` — create a source and run the full pipeline
- `POST /api/style/import` — import style samples and rebuild your profile
- `POST /api/drafts/generate/{source_id}` — regenerate drafts
- `GET /api/drafts` — list all drafts

## 🗺️ Status

Actively built in public. `x-content-mvp` is a working MVP web app; `x-poster` and `youtube-creator` are working terminal agents. Expect rough edges — issues and stars are welcome.

## 🤝 Connect

Built by **Tony (Sheng)** — a Chinese-language teacher with 6000+ students, building AI + Chinese-teaching tools in the open.

If these tools save you time, **⭐ star this repo and [follow @shengdabai](https://github.com/shengdabai)** to see what ships next.

More tools in the same orbit:
- [ai-video-workflow](https://github.com/shengdabai/ai-video-workflow) — end-to-end AI video pipeline
- [ai-video-generator](https://github.com/shengdabai/ai-video-generator) — AI video generation
- [Small-yet-smart-programs](https://github.com/shengdabai/Small-yet-smart-programs) — a collection of small, sharp utilities

## License

No license file yet — all rights reserved by the author until one is added.

---

## 中文

**[English](#-content-creator-hub) | 中文**

[![Last commit](https://img.shields.io/github/last-commit/shengdabai/content-creator-hub)](https://github.com/shengdabai/content-creator-hub/commits)
[![Stars](https://img.shields.io/github/stars/shengdabai/content-creator-hub?style=social)](https://github.com/shengdabai/content-creator-hub/stargazers)
[![Follow @shengdabai](https://img.shields.io/github/followers/shengdabai?style=social)](https://github.com/shengdabai)

> 三个 AI 内容创作工具，带你从灵感直达发布 —— 在终端里完成 X (Twitter) 和 YouTube 内容的撰写、评分与发布。

## 为什么

在 X 和 YouTube 上持续产出内容，意味着要同时应付起草、风格、评分、发布和视频制作。这套工具把整个流程收敛成三个聚焦、自包含的 agent —— 由一位拥有 6000+ 学员的中文老师在公开构建，用来自动化自己的内容发布。

## 是什么

一个 monorepo，包含三个互相独立的工具，共享同一理念：**AI 干重活，你掌方向。**

| 工具 | 作用 | 技术栈 |
|------|------|--------|
| **x-content-mvp** | 把 URL/文本/图片变成已评分的 X 草稿，并学习你的风格的 Web 应用 | Python · FastAPI · OpenAI SDK |
| **x-poster** | 在终端起草并发布推文与推文串到 X 的 agent | Python · Anthropic SDK · X API v2 (tweepy) |
| **youtube-creator** | 在终端撰写脚本、合成并上传 YouTube 视频的 agent | Python · Anthropic SDK · edge-tts · ffmpeg · YouTube Data API v3 |

## ✨ 功能

### x-content-mvp —— X 内容创作 Web 应用
- **洞察提取**：从任意 URL、文本或上传图片中提取核心论点、要点、证据、新颖度、受众价值与可发推角度
- **风格工坊**：导入你的历史推文（文本框 / txt / csv），重建结构化风格画像
- **草稿生成器**：5 种推文类型（`hot_take`、`insight_post`、`thread`、`contrarian`、`personal_brand`）× 3 种语气（`safe`、`sharp`、`bold`）
- **草稿评分**：对 `style_match`、`clarity`、`attention`、`novelty`、`overall` 打分
- **草稿库**：浏览和查询全部草稿，存于本地 SQLite
- **无需 API key 也能用**：缺 key 时退回确定性启发式逻辑，产品始终可用

### x-poster —— 自动化 X 发布 agent
- 通过工具调用式 agent 循环生成推文内容
- 经 API v2 (tweepy) 直接发布单条推文**和**推文串
- 本地草稿保存 + 已发布推文日志
- 回看你最近的推文

### youtube-creator —— AI YouTube 视频 agent
- 工具调用式 agent 循环驱动的 AI 脚本生成
- 素材生成：`edge-tts` 配音 + 自动 SRT 字幕 + 背景图
- 用 `ffmpeg` 合成为最终 MP4
- 经 Data API v3 + OAuth2 上传到 YouTube

## 🧱 技术栈

- **语言：** Python 3.9+
- **Web：** FastAPI · Uvicorn · Jinja2
- **AI：** OpenAI SDK · Anthropic SDK
- **集成：** X API v2 (tweepy) · YouTube Data API v3 · edge-tts · ffmpeg
- **存储：** SQLite（本地）

## 🚀 快速开始

每个工具都在自己的目录中自包含，按需选用。

### x-content-mvp（Web 应用）
```bash
cd x-content-mvp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # 然后填入 OPENAI_API_KEY=YOUR_KEY_HERE
./start.sh                  # 或：uvicorn app.main:app --reload --port 8000
# 打开 http://127.0.0.1:8000
```

### x-poster（终端 agent）
```bash
cd x-poster
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic python-dotenv tweepy
cp .env.example .env        # 填入 ANTHROPIC_API_KEY + X API v2 凭证
python3 x-poster.py
```

### youtube-creator（终端 agent）
```bash
cd youtube-creator
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic python-dotenv edge-tts \
  google-auth-oauthlib google-api-python-client
# 需要 ffmpeg 在 PATH 中（brew install ffmpeg）
cp .env.example .env        # 填入 ANTHROPIC_API_KEY + YouTube OAuth 凭证
python3 youtube-creator.py
```

> 🔑 密钥放在各工具的 `.env` 文件中（已 gitignore）。请用 `OPENAI_API_KEY=YOUR_KEY_HERE` 之类的占位符 —— 切勿提交真实密钥。

## 📖 使用

**环境变量**（每个工具都自带 `.env.example`）：

| 工具 | 必需变量 |
|------|----------|
| x-content-mvp | `OPENAI_API_KEY` |
| x-poster | `ANTHROPIC_API_KEY`、`X_API_KEY`、`X_API_SECRET`、`X_ACCESS_TOKEN`、`X_ACCESS_TOKEN_SECRET` |
| youtube-creator | `ANTHROPIC_API_KEY`、`YOUTUBE_CLIENT_ID`、`YOUTUBE_CLIENT_SECRET` |

**x-content-mvp 主要接口：**
- `POST /api/sources` —— 创建来源并运行完整流水线
- `POST /api/style/import` —— 导入风格样本并重建画像
- `POST /api/drafts/generate/{source_id}` —— 重新生成草稿
- `GET /api/drafts` —— 列出全部草稿

## 🗺️ 状态

在公开构建中。`x-content-mvp` 是可运行的 MVP Web 应用；`x-poster` 和 `youtube-creator` 是可运行的终端 agent。会有粗糙之处 —— 欢迎提 issue 和 star。

## 🤝 联系

由 **Tony (Sheng)** 构建 —— 一位拥有 6000+ 学员的中文老师，在公开打造 AI + 中文教学工具。

如果这些工具帮你省了时间，欢迎 **⭐ star 本仓库并 [关注 @shengdabai](https://github.com/shengdabai)**，看看接下来会发布什么。

同系列的更多工具：
- [ai-video-workflow](https://github.com/shengdabai/ai-video-workflow) —— 端到端 AI 视频流水线
- [ai-video-generator](https://github.com/shengdabai/ai-video-generator) —— AI 视频生成
- [Small-yet-smart-programs](https://github.com/shengdabai/Small-yet-smart-programs) —— 一组小而精的实用工具

## 许可证

暂无许可证文件 —— 在添加之前，作者保留所有权利。
