from collections import Counter
from typing import Dict, List

from app.services.ai_client import AIError, chat_json, has_api_key


def _fallback_profile(samples: List[str], manual_guide: str) -> Dict[str, List[str]]:
    words = []
    for post in samples:
        words.extend([w.strip(".,!?;:()[]{}\"'").lower() for w in post.split()])
    words = [w for w in words if len(w) > 3]
    top_words = [w for w, _ in Counter(words).most_common(12)]

    hooks = []
    for line in samples[:50]:
        txt = line.strip()
        if not txt:
            continue
        first = txt.split(".")[0]
        hooks.append(first[:90])
        if len(hooks) >= 8:
            break

    return {
        "voice_traits": [
            "direct and opinionated",
            "experience-driven, not theoretical",
            "concise — every word earns its place",
            "conversational but authoritative",
        ],
        "preferred_hooks": hooks[:6] or [
            "Most people get this wrong:",
            "Hard truth:",
            "Nobody talks about this, but:",
            "After building this, here's what I know:",
        ],
        "forbidden_patterns": [
            "generic motivational fluff",
            "vague clichés like 'hustle harder'",
            "excessive hashtags",
            "AI-sounding corporate speak",
            "empty hype without substance",
        ],
        "topic_pillars": top_words[:6] or [
            "Chinese language teaching",
            "AI product development",
            "solo entrepreneurship",
            "international trade",
        ],
        "cta_preferences": [
            "ask a precise, specific question",
            "invite constructive disagreement",
            "prompt readers to share their experience",
        ],
        "thread_preferences": [
            "start with the sharpest claim as hook",
            "one idea per tweet, build momentum",
            "close with actionable takeaway + CTA",
        ],
    }


def build_style_profile(samples: List[str], manual_guide: str) -> Dict[str, List[str]]:
    if not samples and not manual_guide.strip():
        return _fallback_profile(samples, manual_guide)

    if not has_api_key():
        return _fallback_profile(samples, manual_guide)

    sample_blob = "\n---\n".join(samples[:120])
    prompt = (
        "You are a senior social writing editor.\n"
        "Extract a robust writing style profile from historical posts and manual guide.\n"
        "Return JSON only with keys:\n"
        "voice_traits (array of strings, 4-8),\n"
        "preferred_hooks (array of strings, 5-10),\n"
        "forbidden_patterns (array of strings, 5-10),\n"
        "topic_pillars (array of strings, 4-10),\n"
        "cta_preferences (array of strings, 3-8),\n"
        "thread_preferences (array of strings, 3-8).\n"
        "Keep every item concise. Use English."
    )
    user_text = (
        f"Manual style guide:\n{manual_guide.strip() or '(none)'}\n\n"
        f"Historical posts:\n{sample_blob or '(none)'}"
    )

    try:
        obj = chat_json(system_prompt=prompt, user_text=user_text, temperature=0.2, max_tokens=1200)
    except AIError:
        return _fallback_profile(samples, manual_guide)

    profile = {
        "voice_traits": _clean_list(obj.get("voice_traits"), 8),
        "preferred_hooks": _clean_list(obj.get("preferred_hooks"), 10),
        "forbidden_patterns": _clean_list(obj.get("forbidden_patterns"), 10),
        "topic_pillars": _clean_list(obj.get("topic_pillars"), 10),
        "cta_preferences": _clean_list(obj.get("cta_preferences"), 8),
        "thread_preferences": _clean_list(obj.get("thread_preferences"), 8),
    }
    if not profile["voice_traits"]:
        return _fallback_profile(samples, manual_guide)
    return profile


def _clean_list(value, cap: int) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in out:
            out.append(text[:180])
        if len(out) >= cap:
            break
    return out
