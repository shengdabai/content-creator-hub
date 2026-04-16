from typing import Any, Dict, List, Optional

from app.services.ai_client import AIError, chat_json, has_api_key


POST_TYPES = ["hot_take", "insight_post", "thread", "contrarian", "personal_brand", "question_post", "list_post"]
TONES = ["safe", "sharp", "bold"]


def extract_insight(
    source_type: str,
    title: str,
    normalized_text: str,
    url: str = "",
    image_data_url: Optional[str] = None,
) -> Dict[str, Any]:
    text = (normalized_text or "").strip()
    if not text and source_type != "image":
        return _fallback_insight(title=title, text="")

    if not has_api_key():
        return _fallback_insight(title=title, text=text)

    prompt = (
        "You are an elite X (Twitter) content strategist who specializes in engagement-driven content.\n"
        "Your audience cares about: Chinese language teaching, AI product development, solo entrepreneurship, international trade.\n"
        "Extract structured, tweet-ready insights that maximize replies, saves, and follows.\n\n"
        "For each input, identify:\n"
        "- The single most provocative or counter-intuitive claim\n"
        "- What 'most people get wrong' about this topic\n"
        "- Personal experience hooks (first-person angles that feel authentic)\n"
        "- Conversation starters (questions that invite qualified replies)\n"
        "- Contrarian or surprising angles that stop the scroll\n\n"
        "Return JSON only with keys:\n"
        "core_claim (string — the single strongest, most specific claim),\n"
        "key_points (string array, 3-8 — concrete, not generic),\n"
        "evidence (string array, 1-6 — real numbers, examples, or cases),\n"
        "novelty (string — what makes this angle fresh),\n"
        "audience_value (string — why your audience would reply/save/share),\n"
        "tweetable_angles (string array, 8-15 — each one a potential post hook, be specific and opinionated),\n"
        "risk_flags (string array, 0-6).\n"
        "Output in English. Every angle must pass the test: 'Would I stop scrolling for this?'"
    )
    user_text = (
        f"source_type: {source_type}\n"
        f"title: {title}\n"
        f"url: {url}\n"
        f"content:\n{text[:12000] or '(image-only input)'}"
    )
    images = [image_data_url] if image_data_url else []

    try:
        obj = chat_json(
            system_prompt=prompt,
            user_text=user_text,
            image_data_urls=images,
            temperature=0.2,
            max_tokens=1600,
        )
    except AIError:
        return _fallback_insight(title=title, text=text)

    return {
        "core_claim": str(obj.get("core_claim", "")).strip()[:600],
        "key_points": _clean_list(obj.get("key_points"), cap=8),
        "evidence": _clean_list(obj.get("evidence"), cap=6),
        "novelty": str(obj.get("novelty", "")).strip()[:600],
        "audience_value": str(obj.get("audience_value", "")).strip()[:600],
        "tweetable_angles": _clean_list(obj.get("tweetable_angles"), cap=12),
        "risk_flags": _clean_list(obj.get("risk_flags"), cap=6),
    }


def generate_drafts(
    insight: Dict[str, Any],
    style_profile: Dict[str, Any],
) -> List[Dict[str, str]]:
    if not has_api_key():
        return _fallback_drafts(insight, style_profile)

    combos = [{"post_type": p, "tone": t} for p in POST_TYPES for t in TONES]

    prompt = (
        "You are an elite X (Twitter) ghostwriter who drives engagement, replies, and follows.\n"
        "Your creator's niche: Chinese language teaching, AI product development, solo entrepreneurship, international trade.\n\n"
        "ENGAGEMENT RULES (non-negotiable):\n"
        "1) First line = scroll-stopping hook. No 'I think' or 'In my opinion'. Start with tension, surprise, or a bold claim.\n"
        "2) Single posts: <= 260 chars. Every word must earn its place.\n"
        "3) Threads: 5-8 tweets split by double newline. First tweet = hook. Last tweet = CTA that drives replies.\n"
        "4) question_post: End with a genuine, specific question that qualified people want to answer.\n"
        "5) list_post: '5 things I learned...' or '3 mistakes...' format. Concrete, numbered, save-worthy.\n"
        "6) NEVER use hashtags. NEVER use generic motivational fluff.\n"
        "7) Write like a real person sharing hard-won experience, not an AI summarizer.\n"
        "8) Every post must have a clear CTA: ask a question, invite disagreement, or prompt a specific action.\n"
        "9) Use pattern interrupts: short sentences after long ones, unexpected turns, specific numbers.\n"
        "10) contrarian posts should genuinely challenge mainstream thinking with evidence.\n"
        "11) personal_brand posts should feel like authentic stories with a concrete lesson.\n\n"
        "Return JSON only with key drafts: array of objects with exactly keys "
        "post_type, tone, content.\n"
        "Must cover all requested post_type + tone combinations exactly once."
    )
    user_text = (
        f"style_profile: {style_profile}\n"
        f"insight: {insight}\n"
        f"required_combinations: {combos}"
    )

    try:
        obj = chat_json(system_prompt=prompt, user_text=user_text, temperature=0.7, max_tokens=3000)
    except AIError:
        return _fallback_drafts(insight, style_profile)

    drafts_raw = obj.get("drafts", [])
    if not isinstance(drafts_raw, list):
        return _fallback_drafts(insight, style_profile)

    clean: List[Dict[str, str]] = []
    seen = set()
    for item in drafts_raw:
        if not isinstance(item, dict):
            continue
        post_type = str(item.get("post_type", "")).strip()
        tone = str(item.get("tone", "")).strip()
        content = str(item.get("content", "")).strip()
        key = (post_type, tone)
        if post_type not in POST_TYPES or tone not in TONES or not content or key in seen:
            continue
        seen.add(key)
        clean.append({"post_type": post_type, "tone": tone, "content": content[:3000]})

    if len(clean) < len(POST_TYPES) * len(TONES):
        fallback = _fallback_drafts(insight, style_profile)
        for f in fallback:
            key = (f["post_type"], f["tone"])
            if key not in seen:
                seen.add(key)
                clean.append(f)
    return clean


def score_drafts(
    drafts: List[Dict[str, Any]],
    insight: Dict[str, Any],
    style_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not drafts:
        return []

    if not has_api_key():
        return _fallback_scores(drafts)

    prompt = (
        "You are a strict content quality scorer for X (Twitter) drafts, optimized for engagement and growth.\n"
        "Creator's niche: Chinese teaching, AI products, solo entrepreneurship, international trade.\n\n"
        "Score each draft on 0-10 scale for:\n"
        "style_match — how well it matches the creator's voice and niche\n"
        "clarity — is the message instantly clear? no ambiguity?\n"
        "attention — does the first line stop the scroll? is it hook-worthy?\n"
        "novelty — is this a fresh angle or just recycled wisdom?\n"
        "risk — potential for controversy/misinformation/brand damage (0=safe, 10=very risky)\n"
        "engagement — will this drive replies, saves, and follows? does it invite conversation?\n\n"
        "overall = 0.20*style_match + 0.15*clarity + 0.20*attention + 0.10*novelty + 0.05*(10-risk) + 0.30*engagement\n\n"
        "Return JSON only with key scores: array of objects:\n"
        "index (int), style_match, clarity, attention, novelty, risk, engagement, overall, rationale (string <= 160 chars)."
    )
    compact_drafts = [
        {
            "index": idx,
            "post_type": d.get("post_type", ""),
            "tone": d.get("tone", ""),
            "content": d.get("content", ""),
        }
        for idx, d in enumerate(drafts)
    ]
    user_text = (
        f"style_profile: {style_profile}\n"
        f"insight: {insight}\n"
        f"drafts: {compact_drafts}"
    )

    try:
        obj = chat_json(system_prompt=prompt, user_text=user_text, temperature=0.1, max_tokens=2200)
    except AIError:
        return _fallback_scores(drafts)

    items = obj.get("scores", [])
    if not isinstance(items, list):
        return _fallback_scores(drafts)

    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(drafts):
            continue
        s1 = _clamp_score(item.get("style_match"))
        s2 = _clamp_score(item.get("clarity"))
        s3 = _clamp_score(item.get("attention"))
        s4 = _clamp_score(item.get("novelty"))
        s5 = _clamp_score(item.get("risk"))
        s6 = _clamp_score(item.get("engagement"))
        overall = _clamp_score(item.get("overall"))
        out.append(
            {
                "index": idx,
                "style_match": s1,
                "clarity": s2,
                "attention": s3,
                "novelty": s4,
                "risk": s5,
                "engagement": s6,
                "overall": overall,
                "rationale": str(item.get("rationale", "")).strip()[:220],
            }
        )

    if not out:
        return _fallback_scores(drafts)

    scored_indices = {s["index"] for s in out}
    for idx, draft in enumerate(drafts):
        if idx not in scored_indices:
            fallback = _fallback_scores([draft])
            fallback[0]["index"] = idx
            out.append(fallback[0])

    out.sort(key=lambda x: x["index"])
    return out


def _fallback_insight(title: str, text: str) -> Dict[str, Any]:
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    core = title or (lines[0][:220] if lines else "A practical insight worth sharing.")
    key_points = []
    for ln in lines:
        if len(key_points) >= 5:
            break
        if len(ln) > 40:
            key_points.append(ln[:180])
    if not key_points:
        key_points = [
            "This challenges conventional thinking in the space",
            "Concrete implication for builders and educators",
            "Actionable takeaway you can apply this week",
        ]
    return {
        "core_claim": core,
        "key_points": key_points[:8],
        "evidence": lines[1:3] if len(lines) > 2 else ["Based on direct experience building and teaching."],
        "novelty": "Connects this to the intersection of AI, language education, and solo business building.",
        "audience_value": "Sparks conversation among builders, educators, and global entrepreneurs.",
        "tweetable_angles": [
            "what most people get wrong about this",
            "the counter-intuitive lesson I learned the hard way",
            "why this matters more than people realize",
            "how this changes the game for solo builders",
            "the question nobody is asking about this",
            "3 things I wish I knew before starting",
            "hot take: this is actually backwards",
            "what teaching Chinese taught me about this",
        ],
        "risk_flags": [],
    }


def _fallback_drafts(insight: Dict[str, Any], style_profile: Dict[str, Any]) -> List[Dict[str, str]]:
    claim = insight.get("core_claim", "This is the core idea.")
    angle = (insight.get("tweetable_angles") or ["practical implication"])[0]
    pillar = (style_profile.get("topic_pillars") or ["AI product development"])[0]

    templates = {
        "hot_take": {
            "safe": f"Here's what nobody tells you: {claim}. The real edge is {angle}.",
            "sharp": f"Stop pretending otherwise: {claim}. {angle} — and most builders still miss this.",
            "bold": f"Unpopular take: {claim}. Everyone's optimizing the wrong thing. {angle} is what actually matters.",
        },
        "insight_post": {
            "safe": f"After 2 years of building: {claim}. The lesson? {angle}. Save this.",
            "sharp": f"Most people get this backwards. {claim}. The real insight: {angle}.",
            "bold": f"I was wrong about {pillar} for years. {claim}. Here's what changed everything: {angle}.",
        },
        "thread": {
            "safe": (
                f"1/ {claim}\n\n"
                f"2/ Most people in {pillar} miss this: {angle}.\n\n"
                "3/ Here's what actually works (from direct experience):\n\n"
                f"4/ The compound effect: doing this consistently for 30 days changes everything.\n\n"
                "5/ What's your experience? Reply with what worked for you."
            ),
            "sharp": (
                f"1/ Hard truth about {pillar} that most creators won't say:\n\n"
                f"2/ {claim}\n\n"
                f"3/ The uncomfortable part: {angle}.\n\n"
                "4/ I learned this the expensive way. Saved you the tuition.\n\n"
                "5/ Here's the one change that flipped everything:\n\n"
                "6/ Agree or disagree? Drop your take below."
            ),
            "bold": (
                f"1/ Everything you've been told about {pillar} is wrong. Here's proof:\n\n"
                f"2/ {claim}\n\n"
                f"3/ {angle} — and nobody talks about it because it's inconvenient.\n\n"
                "4/ What I did differently (and the results):\n\n"
                "5/ The real question: why aren't more people doing this?\n\n"
                "6/ RT if this changed how you think about it. Reply with your biggest pushback."
            ),
        },
        "contrarian": {
            "safe": f"Counter-intuitive: {claim}. Most advice says the opposite. But {angle}. What's your take?",
            "sharp": f"The mainstream is wrong about {pillar}. {claim}. Proof: {angle}. Change my mind.",
            "bold": f"Hot take: the opposite of what everyone says is true. {claim}. {angle}. Fight me on this.",
        },
        "personal_brand": {
            "safe": f"Something I wish I knew earlier: {claim}. Building in {pillar} taught me {angle}.",
            "sharp": f"Year 1: clueless. Year 2: {claim}. The turning point? Realizing {angle}. What's yours?",
            "bold": f"I quit the safe path and went all-in on {pillar}. Best decision ever. {claim}. Here's why: {angle}.",
        },
        "question_post": {
            "safe": f"Genuine question for builders in {pillar}: {claim} — how do you handle {angle}? Reply below.",
            "sharp": f"For everyone building with AI: {claim}. But here's what I can't figure out — {angle}. Who has a better answer?",
            "bold": f"Controversial question: {claim}. Is {angle} actually the right approach? Drop your honest take.",
        },
        "list_post": {
            "safe": (
                f"5 lessons from building in {pillar}:\n\n"
                f"1. {claim}\n"
                f"2. {angle} matters more than you think\n"
                "3. Start before you're ready\n"
                "4. Ship weekly, not monthly\n"
                "5. Talk to users, not just other builders\n\n"
                "Save this. Which one hit hardest?"
            ),
            "sharp": (
                f"3 mistakes everyone makes in {pillar}:\n\n"
                f"1. Ignoring that {claim}\n"
                f"2. Overlooking {angle}\n"
                "3. Building for months without shipping\n\n"
                "I made all 3. Don't repeat my mistakes."
            ),
            "bold": (
                f"7 unpopular truths about {pillar}:\n\n"
                f"1. {claim}\n"
                f"2. {angle}\n"
                "3. Most 'best practices' are just herd behavior\n"
                "4. Solo builders have an unfair advantage\n"
                "5. Speed > perfection, always\n"
                "6. Your audience knows more than you think\n"
                "7. The best marketing is just being useful\n\n"
                "RT the one you disagree with most."
            ),
        },
    }

    drafts: List[Dict[str, str]] = []
    for post_type in POST_TYPES:
        for tone in TONES:
            content = templates.get(post_type, {}).get(
                tone,
                f"{claim}. The edge is {angle}. Most people still miss this.",
            )
            drafts.append({"post_type": post_type, "tone": tone, "content": content[:2800]})
    return drafts


def _fallback_scores(drafts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scored = []
    for idx, draft in enumerate(drafts):
        text = draft.get("content", "")
        post_type = draft.get("post_type", "")
        tone = draft.get("tone", "")
        ln = len(text)
        clarity = 8.0 if 80 <= ln <= 280 else 6.8
        has_hook = any(k in text.lower() for k in ["hard truth", "unpopular", "most people", "stop", "wrong", "nobody"])
        attention = 8.5 if has_hook else 7.0
        novelty = 7.4 if "counter" in text.lower() or "unpopular" in text.lower() else 6.8
        style_match = 7.2
        risk = 2.5 if tone == "bold" else (1.5 if tone == "sharp" else 1.0)
        # Engagement heuristics
        has_question = "?" in text
        has_cta = any(k in text.lower() for k in ["reply", "what's your", "change my mind", "drop your", "which one", "agree or"])
        engagement = 8.5 if (has_question and has_cta) else (7.8 if has_question or has_cta else 6.5)
        if post_type in ("question_post", "list_post", "thread"):
            engagement = min(engagement + 1.0, 10.0)
        overall = round(
            0.20 * style_match + 0.15 * clarity + 0.20 * attention
            + 0.10 * novelty + 0.05 * (10 - risk) + 0.30 * engagement, 2
        )
        scored.append(
            {
                "index": idx,
                "style_match": round(style_match, 2),
                "clarity": round(clarity, 2),
                "attention": round(attention, 2),
                "novelty": round(novelty, 2),
                "risk": round(risk, 2),
                "engagement": round(engagement, 2),
                "overall": overall,
                "rationale": "Fallback heuristic score due to missing/failed AI scoring.",
            }
        )
    return scored


def _clean_list(value: Any, cap: int) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        txt = str(item).strip()
        if txt and txt not in out:
            out.append(txt[:240])
        if len(out) >= cap:
            break
    return out


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    if score < 0:
        return 0.0
    if score > 10:
        return 10.0
    return round(score, 2)
