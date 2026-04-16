import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "x_content_mvp.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _from_json(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _row_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = _row_factory
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS style_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'Default Profile',
                voice_traits TEXT NOT NULL DEFAULT '[]',
                preferred_hooks TEXT NOT NULL DEFAULT '[]',
                forbidden_patterns TEXT NOT NULL DEFAULT '[]',
                topic_pillars TEXT NOT NULL DEFAULT '[]',
                cta_preferences TEXT NOT NULL DEFAULT '[]',
                thread_preferences TEXT NOT NULL DEFAULT '[]',
                manual_guide TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS style_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                post_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES style_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS source_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                raw_input TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                image_path TEXT NOT NULL DEFAULT '',
                normalized_text TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS extracted_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                core_claim TEXT NOT NULL DEFAULT '',
                key_points TEXT NOT NULL DEFAULT '[]',
                evidence TEXT NOT NULL DEFAULT '[]',
                novelty TEXT NOT NULL DEFAULT '',
                audience_value TEXT NOT NULL DEFAULT '',
                tweetable_angles TEXT NOT NULL DEFAULT '[]',
                risk_flags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES source_items(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS generated_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                insight_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                post_type TEXT NOT NULL,
                tone TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES source_items(id) ON DELETE CASCADE,
                FOREIGN KEY (insight_id) REFERENCES extracted_insights(id) ON DELETE CASCADE,
                FOREIGN KEY (profile_id) REFERENCES style_profiles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS draft_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER NOT NULL UNIQUE,
                style_match REAL NOT NULL DEFAULT 0.0,
                clarity REAL NOT NULL DEFAULT 0.0,
                attention REAL NOT NULL DEFAULT 0.0,
                novelty REAL NOT NULL DEFAULT 0.0,
                risk REAL NOT NULL DEFAULT 0.0,
                engagement REAL NOT NULL DEFAULT 0.0,
                overall REAL NOT NULL DEFAULT 0.0,
                rationale TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (draft_id) REFERENCES generated_drafts(id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _migrate_score_columns() -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        columns = [row["name"] for row in cur.execute("PRAGMA table_info(draft_scores)").fetchall()]
        if "risk" not in columns:
            cur.execute("ALTER TABLE draft_scores ADD COLUMN risk REAL NOT NULL DEFAULT 0.0")
        if "engagement" not in columns:
            cur.execute("ALTER TABLE draft_scores ADD COLUMN engagement REAL NOT NULL DEFAULT 0.0")
        conn.commit()
    finally:
        conn.close()


def get_or_create_default_profile() -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT * FROM style_profiles ORDER BY id ASC LIMIT 1").fetchone()
        if row:
            return hydrate_profile(row)

        now = _utc_now()
        cur.execute(
            """
            INSERT INTO style_profiles (
                name, voice_traits, preferred_hooks, forbidden_patterns,
                topic_pillars, cta_preferences, thread_preferences,
                manual_guide, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Default Profile",
                _to_json([
                    "direct and opinionated",
                    "experience-driven, not theoretical",
                    "concise — every word earns its place",
                    "conversational but authoritative",
                    "uses concrete examples over abstractions",
                    "first-person storytelling when relevant",
                ]),
                _to_json([
                    "Most people get this wrong:",
                    "Hard truth about [topic]:",
                    "I spent [time] learning this the hard way:",
                    "Unpopular take:",
                    "Nobody talks about this, but:",
                    "The real reason [X] works:",
                    "Stop doing [common mistake]. Here's why:",
                    "After building [X], here's what I know:",
                ]),
                _to_json([
                    "generic motivational fluff",
                    "vague clichés like 'hustle harder'",
                    "excessive hashtags",
                    "AI-sounding corporate speak",
                    "empty hype without substance",
                    "clickbait without payoff",
                ]),
                _to_json([
                    "Chinese language teaching",
                    "AI product development",
                    "solo entrepreneurship",
                    "international trade",
                    "building in public",
                    "cross-cultural business",
                ]),
                _to_json([
                    "ask a precise, specific question",
                    "invite constructive disagreement",
                    "prompt readers to share their experience",
                    "end with 'What's your take?' or similar",
                    "use 'Reply with...' for targeted responses",
                ]),
                _to_json([
                    "start with the sharpest claim as hook",
                    "one idea per tweet, build momentum",
                    "include a personal anecdote in tweet 3-4",
                    "close with actionable takeaway + CTA",
                    "5-8 tweets optimal length",
                ]),
                "Focus on Chinese teaching, AI products, solo entrepreneurship, and international trade. "
                "Write like a builder sharing real experience. Be specific, opinionated, and invite conversation.",
                now,
            ),
        )
        conn.commit()
        row = cur.execute("SELECT * FROM style_profiles WHERE id = ?", (cur.lastrowid,)).fetchone()
        return hydrate_profile(row)
    finally:
        conn.close()


def hydrate_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "voice_traits": _from_json(row.get("voice_traits"), []),
        "preferred_hooks": _from_json(row.get("preferred_hooks"), []),
        "forbidden_patterns": _from_json(row.get("forbidden_patterns"), []),
        "topic_pillars": _from_json(row.get("topic_pillars"), []),
        "cta_preferences": _from_json(row.get("cta_preferences"), []),
        "thread_preferences": _from_json(row.get("thread_preferences"), []),
        "manual_guide": row.get("manual_guide", ""),
        "updated_at": row.get("updated_at", ""),
    }


def upsert_profile(profile: Dict[str, Any], manual_guide: str, profile_id: Optional[int] = None) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        now = _utc_now()
        target_id = profile_id or get_or_create_default_profile()["id"]
        cur.execute(
            """
            UPDATE style_profiles
            SET
                voice_traits = ?,
                preferred_hooks = ?,
                forbidden_patterns = ?,
                topic_pillars = ?,
                cta_preferences = ?,
                thread_preferences = ?,
                manual_guide = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                _to_json(profile.get("voice_traits", [])),
                _to_json(profile.get("preferred_hooks", [])),
                _to_json(profile.get("forbidden_patterns", [])),
                _to_json(profile.get("topic_pillars", [])),
                _to_json(profile.get("cta_preferences", [])),
                _to_json(profile.get("thread_preferences", [])),
                manual_guide or "",
                now,
                target_id,
            ),
        )
        conn.commit()
        row = cur.execute("SELECT * FROM style_profiles WHERE id = ?", (target_id,)).fetchone()
        return hydrate_profile(row)
    finally:
        conn.close()


def add_style_samples(profile_id: int, samples: Iterable[str]) -> int:
    clean = [s.strip() for s in samples if s and s.strip()]
    if not clean:
        return 0
    conn = get_conn()
    try:
        cur = conn.cursor()
        now = _utc_now()
        cur.executemany(
            "INSERT INTO style_samples (profile_id, post_text, created_at) VALUES (?, ?, ?)",
            [(profile_id, text, now) for text in clean],
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def list_style_samples(profile_id: int, limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        return cur.execute(
            """
            SELECT id, profile_id, post_text, created_at
            FROM style_samples
            WHERE profile_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (profile_id, limit),
        ).fetchall()
    finally:
        conn.close()


def create_source_item(
    source_type: str,
    title: str,
    raw_input: str,
    url: str,
    image_path: str,
    normalized_text: str,
) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        now = _utc_now()
        cur.execute(
            """
            INSERT INTO source_items (
                source_type, title, raw_input, url, image_path, normalized_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source_type, title, raw_input, url, image_path, normalized_text, now),
        )
        conn.commit()
        return cur.execute("SELECT * FROM source_items WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()


def get_source_item(source_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        return cur.execute("SELECT * FROM source_items WHERE id = ?", (source_id,)).fetchone()
    finally:
        conn.close()


def save_insight(source_id: int, insight: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        now = _utc_now()
        cur.execute(
            """
            INSERT INTO extracted_insights (
                source_id, core_claim, key_points, evidence, novelty, audience_value,
                tweetable_angles, risk_flags, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                insight.get("core_claim", ""),
                _to_json(insight.get("key_points", [])),
                _to_json(insight.get("evidence", [])),
                insight.get("novelty", ""),
                insight.get("audience_value", ""),
                _to_json(insight.get("tweetable_angles", [])),
                _to_json(insight.get("risk_flags", [])),
                now,
            ),
        )
        conn.commit()
        row = cur.execute("SELECT * FROM extracted_insights WHERE id = ?", (cur.lastrowid,)).fetchone()
        return hydrate_insight(row)
    finally:
        conn.close()


def hydrate_insight(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    return {
        "id": row["id"],
        "source_id": row["source_id"],
        "core_claim": row["core_claim"],
        "key_points": _from_json(row["key_points"], []),
        "evidence": _from_json(row["evidence"], []),
        "novelty": row["novelty"],
        "audience_value": row["audience_value"],
        "tweetable_angles": _from_json(row["tweetable_angles"], []),
        "risk_flags": _from_json(row["risk_flags"], []),
        "created_at": row["created_at"],
    }


def get_latest_insight_for_source(source_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT * FROM extracted_insights
            WHERE source_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        return hydrate_insight(row)
    finally:
        conn.close()


def save_drafts(
    source_id: int,
    insight_id: int,
    profile_id: int,
    drafts: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    clean = [d for d in drafts if d.get("content", "").strip()]
    if not clean:
        return []
    conn = get_conn()
    try:
        cur = conn.cursor()
        now = _utc_now()
        rows = []
        for draft in clean:
            cur.execute(
                """
                INSERT INTO generated_drafts (
                    source_id, insight_id, profile_id, post_type, tone, content, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    insight_id,
                    profile_id,
                    draft.get("post_type", "insight_post"),
                    draft.get("tone", "safe"),
                    draft.get("content", "").strip(),
                    now,
                ),
            )
            rows.append(
                {
                    "id": cur.lastrowid,
                    "source_id": source_id,
                    "insight_id": insight_id,
                    "profile_id": profile_id,
                    "post_type": draft.get("post_type", "insight_post"),
                    "tone": draft.get("tone", "safe"),
                    "content": draft.get("content", "").strip(),
                    "created_at": now,
                }
            )
        conn.commit()
        return rows
    finally:
        conn.close()


def save_scores(scores: Iterable[Dict[str, Any]]) -> None:
    conn = get_conn()
    try:
        cur = conn.cursor()
        now = _utc_now()
        for score in scores:
            cur.execute(
                """
                INSERT INTO draft_scores (
                    draft_id, style_match, clarity, attention, novelty, risk, engagement, overall, rationale, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(draft_id) DO UPDATE SET
                    style_match = excluded.style_match,
                    clarity = excluded.clarity,
                    attention = excluded.attention,
                    novelty = excluded.novelty,
                    risk = excluded.risk,
                    engagement = excluded.engagement,
                    overall = excluded.overall,
                    rationale = excluded.rationale,
                    created_at = excluded.created_at
                """,
                (
                    score["draft_id"],
                    float(score.get("style_match", 0)),
                    float(score.get("clarity", 0)),
                    float(score.get("attention", 0)),
                    float(score.get("novelty", 0)),
                    float(score.get("risk", 0)),
                    float(score.get("engagement", 0)),
                    float(score.get("overall", 0)),
                    score.get("rationale", ""),
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_source_drafts(source_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        return cur.execute(
            """
            SELECT
                d.*,
                s.style_match,
                s.clarity,
                s.attention,
                s.novelty,
                s.risk,
                s.engagement,
                s.overall,
                s.rationale
            FROM generated_drafts d
            LEFT JOIN draft_scores s ON d.id = s.draft_id
            WHERE d.source_id = ?
            ORDER BY COALESCE(s.overall, 0) DESC, d.id DESC
            """,
            (source_id,),
        ).fetchall()
    finally:
        conn.close()


def list_drafts(limit: int = 120) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        return cur.execute(
            """
            SELECT
                d.id,
                d.post_type,
                d.tone,
                d.content,
                d.created_at,
                d.source_id,
                src.title AS source_title,
                src.source_type,
                COALESCE(s.overall, 0) AS overall,
                COALESCE(s.style_match, 0) AS style_match,
                COALESCE(s.clarity, 0) AS clarity,
                COALESCE(s.attention, 0) AS attention,
                COALESCE(s.novelty, 0) AS novelty,
                COALESCE(s.risk, 0) AS risk,
                COALESCE(s.engagement, 0) AS engagement,
                COALESCE(s.rationale, '') AS rationale
            FROM generated_drafts d
            JOIN source_items src ON d.source_id = src.id
            LEFT JOIN draft_scores s ON d.id = s.draft_id
            ORDER BY d.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()


def get_draft(draft_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        return cur.execute(
            """
            SELECT
                d.*,
                COALESCE(s.style_match, 0) AS style_match,
                COALESCE(s.clarity, 0) AS clarity,
                COALESCE(s.attention, 0) AS attention,
                COALESCE(s.novelty, 0) AS novelty,
                COALESCE(s.risk, 0) AS risk,
                COALESCE(s.engagement, 0) AS engagement,
                COALESCE(s.overall, 0) AS overall,
                COALESCE(s.rationale, '') AS rationale
            FROM generated_drafts d
            LEFT JOIN draft_scores s ON d.id = s.draft_id
            WHERE d.id = ?
            """,
            (draft_id,),
        ).fetchone()
    finally:
        conn.close()


def dashboard_stats() -> Dict[str, int]:
    conn = get_conn()
    try:
        cur = conn.cursor()
        total_sources = cur.execute("SELECT COUNT(1) AS c FROM source_items").fetchone()["c"]
        total_drafts = cur.execute("SELECT COUNT(1) AS c FROM generated_drafts").fetchone()["c"]
        total_samples = cur.execute("SELECT COUNT(1) AS c FROM style_samples").fetchone()["c"]
        return {
            "total_sources": total_sources,
            "total_drafts": total_drafts,
            "total_style_samples": total_samples,
        }
    finally:
        conn.close()
