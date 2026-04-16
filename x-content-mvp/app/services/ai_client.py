import json
from typing import Any, Dict, List, Optional

import requests

from app.config import AI_MODEL, AI_TIMEOUT_SECONDS, OPENAI_API_KEY, OPENAI_BASE_URL


class AIError(RuntimeError):
    pass


def has_api_key() -> bool:
    return bool(OPENAI_API_KEY)


def _extract_content_text(message: Dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") in {"text", "output_text"} and item.get("text"):
                    parts.append(str(item["text"]))
        return "\n".join(parts).strip()
    return str(content)


def chat_json(
    *,
    system_prompt: str,
    user_text: str,
    image_data_urls: Optional[List[str]] = None,
    temperature: float = 0.4,
    max_tokens: int = 1600,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    if not has_api_key():
        raise AIError("OPENAI_API_KEY is not set.")

    user_content: List[Dict[str, Any]] = [{"type": "text", "text": user_text}]
    for data_url in image_data_urls or []:
        user_content.append({"type": "image_url", "image_url": {"url": data_url}})

    payload: Dict[str, Any] = {
        "model": model or AI_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    response = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=AI_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise AIError(f"AI request failed ({response.status_code}): {response.text[:300]}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise AIError("AI response has no choices.")
    raw = _extract_content_text(choices[0].get("message", {})).strip()
    if not raw:
        raise AIError("AI response content is empty.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"AI returned non-JSON output: {raw[:300]}") from exc
