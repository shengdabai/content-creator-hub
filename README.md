# Content Creator Hub

A collection of AI-powered content creation tools for X (Twitter) and YouTube. Automate content generation, posting, and video management.

内容创作工具集 -- 基于 AI 的 X (Twitter) 和 YouTube 内容创作工具集合，自动化内容生成、发布和视频管理。

## Tools / 工具

### X Content MVP / X 内容创作
Full-featured English content creation pipeline with style learning, content generation, and publishing workflow.

Features:
- Style engine that learns from existing posts
- Multi-format content generation (thread, single post, reply)
- Content pipeline with AI-powered drafting and refinement
- Web UI for content review and editing

Tech: Python, FastAPI, OpenAI SDK

### X Poster / X 推文发布
Automated X/Twitter posting agent powered by AI.

Features:
- AI-generated post content
- Direct posting to X via API v2
- Draft management and preview
- Scheduled posting support

Tech: Python, Anthropic SDK (Kimi), X API v2

### YouTube Creator / YouTube 视频创作
AI-powered YouTube video content creation and management tool.

Features:
- AI-generated video scripts and descriptions
- YouTube Data API integration for uploads
- Draft management with revision history
- OAuth2 authentication flow

Tech: Python, Anthropic SDK (Kimi), YouTube Data API v3

## Getting Started / 快速开始

Each tool is self-contained in its own directory:

```bash
# X Content MVP
cd x-content-mvp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your API keys
./start.sh

# X Poster
cd x-poster
pip install -r requirements.txt  # or just run with python3
cp .env.example .env  # Fill in X API credentials
python x-poster.py

# YouTube Creator
cd youtube-creator
pip install -r requirements.txt  # or just run with python3
cp .env.example .env  # Fill in YouTube OAuth credentials
python youtube-creator.py
```

## Environment Variables / 环境变量

Each tool has its own `.env.example` file. Required keys:

| Tool | Variables |
|------|-----------|
| X Content MVP | `OPENAI_API_KEY` |
| X Poster | `ANTHROPIC_API_KEY`, `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` |
| YouTube Creator | `ANTHROPIC_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` |

## Security / 安全说明

- API keys are stored locally in `.env` files (gitignored)
- Keys are never committed to the repository
- OAuth tokens are stored locally only

## License

Private repository. All rights reserved.
