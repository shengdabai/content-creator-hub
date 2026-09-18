#!/usr/bin/env python3
"""
X/Twitter Poster Agent - 自动编写内容并发布到 X

工具: read_file, write_file, post_tweet, post_thread, get_my_tweets
"""

import os
import json
import stat
import sys
import uuid
from pathlib import Path
from datetime import datetime

try:
    import readline
    readline.parse_and_bind('set input-meta on')
    readline.parse_and_bind('set output-meta on')
except ImportError:
    pass

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ.get("MODEL_ID", "claude-opus-4-5")
WORKDIR = Path.cwd()
DRAFTS_DIR = WORKDIR / "drafts"
if DRAFTS_DIR.exists() and (DRAFTS_DIR.is_symlink() or not DRAFTS_DIR.is_dir()):
    raise RuntimeError(f"Unsafe drafts directory: {DRAFTS_DIR}")
DRAFTS_DIR.mkdir(mode=0o700, exist_ok=True)
MAX_DRAFT_BYTES = 100_000

SYSTEM = f"""你是一个专业的 X/Twitter 内容创作 agent，工作目录: {WORKDIR}

你的能力:
1. 根据用户主题创作高质量推文（单条或 Thread）
2. 管理草稿（保存、编辑、预览）
3. 发布到 X/Twitter
4. 查看已发布的推文

写作风格指南:
- 简洁有力，每条推文控制在 280 字符内（中文约 140 字）
- Thread 的第一条要有 hook（吸引力开头）
- 善用 emoji 但不过度
- 适当使用 hashtag（2-3 个）
- 有观点、有态度，避免平淡无味
- 结尾可以用 CTA 引导互动

Thread 写作技巧:
- 第 1 条: Hook — 吸引注意力的核心观点
- 中间: 论据、案例、数据
- 最后 1 条: 总结 + CTA（转发/关注/讨论）
- 每条之间要有逻辑连贯性，建议 3-10 条

工作流程:
1. 收到主题后，先生成草稿用 write_file 保存到 drafts/
2. 展示给用户确认
3. 确认后用 post_tweet 或 post_thread 发布

规则: 发布前务必先展示完整内容让用户确认
"""

TOOLS = [
    {
        "name": "read_file",
        "description": "只读取 drafts/ 目录下的单个草稿文件",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "只写入 drafts/ 目录下的单个草稿文件",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "post_tweet",
        "description": "发布单条推文到 X/Twitter",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "推文内容，最多 280 字符"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "post_thread",
        "description": "发布推文串 (Thread)，按顺序发布多条推文并自动串联",
        "input_schema": {
            "type": "object",
            "properties": {
                "tweets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "推文列表，每条最多 280 字符",
                },
            },
            "required": ["tweets"],
        },
    },
    {
        "name": "get_my_tweets",
        "description": "获取最近发布的推文",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "获取数量，默认 5"},
            },
        },
    },
]


def run_bash(command: str) -> str:
    """Compatibility stub: shell execution is intentionally disabled."""
    return "Error: shell tool is disabled"


def _draft_filename(path: str) -> str:
    if not isinstance(path, str) or not path.strip() or "\x00" in path:
        raise ValueError("Draft path must be a non-empty string")
    raw = Path(path)
    if raw.is_absolute():
        if raw.parent != DRAFTS_DIR:
            raise ValueError("Draft path must be directly inside drafts/")
        name = raw.name
    else:
        parts = raw.parts
        if len(parts) == 2 and parts[0] == DRAFTS_DIR.name:
            name = parts[1]
        elif len(parts) == 1:
            name = parts[0]
        else:
            raise ValueError("Draft path must be drafts/<filename>")
    lowered = name.lower()
    secret_name = (
        lowered.startswith(".")
        or lowered in {"auth.json", ".npmrc"}
        or lowered.startswith("id_rsa")
        or lowered.startswith("credentials.")
        or lowered.startswith("secrets.")
        or lowered.endswith((".key", ".pem"))
    )
    if name in {".", ".."} or secret_name:
        raise ValueError("Hidden, secret, and credential filenames are not allowed")
    return name


def _open_drafts_dir() -> int:
    required_dir_fd = (os.open, os.stat, os.unlink, os.rename)
    if (
        not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or any(function not in os.supports_dir_fd for function in required_dir_fd)
    ):
        raise RuntimeError("Platform lacks required no-follow draft file operations")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    return os.open(DRAFTS_DIR, flags)


def _validate_regular_single_link(file_stat: os.stat_result) -> None:
    if not stat.S_ISREG(file_stat.st_mode):
        raise ValueError("Draft must be a regular file")
    if file_stat.st_nlink != 1:
        raise ValueError("Hard-linked drafts are not allowed")


def _atomic_replace(directory_fd: int, source: str, destination: str) -> None:
    os.rename(source, destination, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)


def _write_draft_file(path: str, content: str) -> Path:
    if not isinstance(content, str):
        raise ValueError("Draft content must be text")
    payload = content.encode("utf-8")
    if len(payload) > MAX_DRAFT_BYTES:
        raise ValueError(f"Draft exceeds {MAX_DRAFT_BYTES} bytes")
    name = _draft_filename(path)
    directory_fd = _open_drafts_dir()
    temp_name = f".{name}.{uuid.uuid4().hex}.tmp"
    temp_fd = None
    try:
        try:
            existing = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            _validate_regular_single_link(existing)

        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        temp_fd = os.open(temp_name, flags, 0o600, dir_fd=directory_fd)
        view = memoryview(payload)
        while view:
            written = os.write(temp_fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None
        _atomic_replace(directory_fd, temp_name, name)
    except Exception:
        if temp_fd is not None:
            os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(directory_fd)
    return DRAFTS_DIR / name


def run_read_file(path: str) -> str:
    try:
        name = _draft_filename(path)
        directory_fd = _open_drafts_dir()
        try:
            flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
            file_fd = os.open(name, flags, dir_fd=directory_fd)
            try:
                file_stat = os.fstat(file_fd)
                _validate_regular_single_link(file_stat)
                if file_stat.st_size > MAX_DRAFT_BYTES:
                    raise ValueError(f"Draft exceeds {MAX_DRAFT_BYTES} bytes")
                chunks = []
                remaining = MAX_DRAFT_BYTES + 1
                while remaining:
                    chunk = os.read(file_fd, min(65536, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                payload = b"".join(chunks)
                if len(payload) > MAX_DRAFT_BYTES:
                    raise ValueError(f"Draft exceeds {MAX_DRAFT_BYTES} bytes")
                return payload.decode("utf-8")
            finally:
                os.close(file_fd)
        finally:
            os.close(directory_fd)
    except Exception as e:
        return f"Error: {e}"


def run_write_file(path: str, content: str) -> str:
    try:
        draft_path = _write_draft_file(path, content)
        return f"已写入 {len(content.encode('utf-8'))} 字节到 {draft_path}"
    except Exception as e:
        return f"Error: {e}"


def get_x_client():
    try:
        import tweepy
    except ImportError:
        return None, "Error: tweepy 未安装。请运行: pip install tweepy"

    api_key = os.getenv("X_API_KEY", "")
    if not api_key or api_key == "你的API_KEY":
        return None, (
            "Error: X API 未配置。请完成以下步骤:\n"
            "1. 访问 https://developer.x.com/en/portal/dashboard\n"
            "2. 创建 App (Free tier 即可发推)\n"
            "3. 获取 API Key/Secret + Access Token/Secret (Read and Write 权限)\n"
            "4. 填入 .env 文件"
        )

    x = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=os.getenv("X_API_SECRET", ""),
        access_token=os.getenv("X_ACCESS_TOKEN", ""),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", ""),
    )
    return x, None


def log_tweet(tweet_id: str, text: str, is_thread=False, thread_index=0):
    log_file = WORKDIR / "post_history.jsonl"
    entry = {
        "id": tweet_id, "text": text, "is_thread": is_thread,
        "thread_index": thread_index, "posted_at": datetime.now().isoformat(),
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _save_draft(content, draft_type="tweet") -> str:
    """保存草稿文件，返回路径"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_path = _write_draft_file(f"{draft_type}_{ts}_{uuid.uuid4().hex}.txt", content)
    return str(draft_path)


def _contains_unsafe_terminal_text(content: str) -> bool:
    bidi_controls = {
        "\u061c", "\u200e", "\u200f",
        "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
        "\u2066", "\u2067", "\u2068", "\u2069",
    }
    for character in content:
        codepoint = ord(character)
        if (codepoint < 0x20 and character not in {"\n", "\t"}):
            return True
        if 0x7F <= codepoint <= 0x9F or character in bidi_controls:
            return True
    return False


def _confirm_publish(kind: str, content: str) -> bool:
    """Require a human at a real terminal to approve the exact rendered content."""
    if _contains_unsafe_terminal_text(content):
        print("Error: content contains unsafe terminal control characters; publishing blocked.")
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    print(f"\n===== {kind} 待发布完整内容 =====")
    print(content)
    print("===== 内容结束 =====")
    try:
        answer = input("请输入 PUBLISH 确认发布：")
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip() == "PUBLISH"


def _try_api_post(text: str):
    """尝试通过 API 发推，成功返回 tweet_id，失败返回 None"""
    x, err = get_x_client()
    if err:
        return None
    try:
        response = x.create_tweet(text=text)
        return response.data["id"]
    except Exception:
        return None


def run_post_tweet(text: str) -> str:
    if len(text) > 280:
        return f"Error: 推文超过 280 字符 (当前 {len(text)} 字符)"

    if not _confirm_publish("单条推文", text):
        draft_path = _save_draft(text, "tweet")
        log_tweet("draft", text)
        return f"发布已取消，草稿已保存: {draft_path}"

    # 尝试 API 发布
    tweet_id = _try_api_post(text)
    if tweet_id:
        log_tweet(tweet_id, text)
        return f"发布成功!\nURL: https://x.com/i/status/{tweet_id}"

    # API 失败，保存草稿
    draft_path = _save_draft(text, "tweet")
    log_tweet("draft", text)
    return (
        f"API 暂不可用，已保存为草稿: {draft_path}\n\n"
        f"请手动发布 — 复制以下内容到 X:\n"
        f"{'='*40}\n{text}\n{'='*40}\n\n"
        f"发布链接: https://x.com/compose/post"
    )


def run_post_thread(tweets: list) -> str:
    for i, t in enumerate(tweets):
        if len(t) > 280:
            return f"Error: 第 {i+1} 条推文超过 280 字符 ({len(t)} 字符)"

    thread_text = "\n\n---\n\n".join(f"[{i+1}/{len(tweets)}]\n{t}" for i, t in enumerate(tweets))
    if not _confirm_publish("Thread", thread_text):
        draft_path = _save_draft(thread_text, "thread")
        for i, t in enumerate(tweets):
            log_tweet("draft", t, is_thread=True, thread_index=i)
        return f"发布已取消，草稿已保存: {draft_path}"

    # 尝试 API 发布
    x, err = get_x_client()
    api_ok = err is None
    if api_ok:
        results = []
        reply_to = None
        try:
            for i, tweet_text in enumerate(tweets):
                kwargs = {"text": tweet_text}
                if reply_to:
                    kwargs["in_reply_to_tweet_id"] = reply_to
                response = x.create_tweet(**kwargs)
                tweet_id = response.data["id"]
                reply_to = tweet_id
                results.append(f"  [{i+1}/{len(tweets)}] https://x.com/i/status/{tweet_id}")
                log_tweet(tweet_id, tweet_text, is_thread=True, thread_index=i)
            return f"Thread 发布成功! ({len(tweets)} 条)\n" + "\n".join(results)
        except Exception:
            api_ok = False

    # API 失败，保存草稿
    draft_path = _save_draft(thread_text, "thread")
    for i, t in enumerate(tweets):
        log_tweet("draft", t, is_thread=True, thread_index=i)
    return (
        f"API 暂不可用，已保存为草稿: {draft_path}\n\n"
        f"请手动发布 Thread — 逐条复制到 X:\n"
        f"{'='*40}\n{thread_text}\n{'='*40}\n\n"
        f"发布链接: https://x.com/compose/post"
    )


def run_get_my_tweets(count: int = 5) -> str:
    x, err = get_x_client()
    if err:
        return err
    try:
        me = x.get_me()
        response = x.get_users_tweets(
            id=me.data.id, max_results=min(count, 100),
            tweet_fields=["created_at", "public_metrics"],
        )
        if not response.data:
            return "暂无推文"
        lines = []
        for tweet in response.data:
            m = tweet.public_metrics or {}
            lines.append(
                f"[{tweet.created_at}] {tweet.text[:80]}...\n"
                f"  likes:{m.get('like_count',0)} rt:{m.get('retweet_count',0)} reply:{m.get('reply_count',0)}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def execute_tool(name: str, args: dict) -> str:
    dispatch = {
        "read_file": lambda: run_read_file(args["path"]),
        "write_file": lambda: run_write_file(args["path"], args["content"]),
        "post_tweet": lambda: run_post_tweet(args["text"]),
        "post_thread": lambda: run_post_thread(args["tweets"]),
        "get_my_tweets": lambda: run_get_my_tweets(args.get("count", 5)),
    }
    return dispatch.get(name, lambda: f"Unknown tool: {name}")()


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL, system=SYSTEM, messages=messages,
            tools=TOOLS, max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\033[33m> {block.name}\033[0m: {str(block.input)[:120]}")
                output = execute_tool(block.name, block.input)
                print(output[:300])
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("X/Twitter Poster Agent")
    print(f"工作目录: {WORKDIR}")
    print(f"草稿目录: {DRAFTS_DIR}")
    print("输入主题开始创作，输入 q 退出\n")

    history = []
    while True:
        try:
            query = input("\033[36mx-post >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        last = history[-1]["content"]
        if isinstance(last, list):
            for block in last:
                if hasattr(block, "text"):
                    print(block.text)
        print()
