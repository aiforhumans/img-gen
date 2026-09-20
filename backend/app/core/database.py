import json
import aiosqlite
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.app.core.config import PROJECT_ROOT
from backend.app.core.logger import app_logger

DB_PATH = PROJECT_ROOT / "outputs" / "gallery.db"

INIT_SQL = """
CREATE TABLE IF NOT EXISTS generations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT DEFAULT '',
    negative_prompt TEXT DEFAULT '',
    model TEXT NOT NULL,
    model_version TEXT DEFAULT '',
    loras TEXT DEFAULT '[]',
    seed INTEGER NOT NULL,
    steps INTEGER NOT NULL,
    guidance REAL NOT NULL,
    sampler TEXT DEFAULT '',
    scheduler TEXT DEFAULT '',
    style TEXT DEFAULT 'none',
    aspect_ratio TEXT DEFAULT '1:1',
    quality TEXT DEFAULT 'balanced',
    mode TEXT DEFAULT 'auto',
    oom_retries INTEGER DEFAULT 0,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    generation_time REAL DEFAULT 0.0,
    peak_vram_mb REAL DEFAULT 0.0,
    vram_strategy TEXT DEFAULT 'BALANCED',
    gpu_name TEXT DEFAULT '',
    image_path TEXT NOT NULL,
    thumbnail_path TEXT DEFAULT '',
    is_favorite INTEGER DEFAULT 0,
    rating INTEGER DEFAULT 0,
    tags TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_generations_created_at ON generations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generations_model ON generations(model);
CREATE INDEX IF NOT EXISTS idx_generations_favorite ON generations(is_favorite);
"""

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(INIT_SQL)

        # Migration: ensure newly introduced columns exist in case table was created earlier
        cursor = await db.execute("PRAGMA table_info(generations)")
        columns = [row[1] for row in await cursor.fetchall()]
        new_cols = [
            ("style", "TEXT DEFAULT 'none'"),
            ("aspect_ratio", "TEXT DEFAULT '1:1'"),
            ("quality", "TEXT DEFAULT 'balanced'"),
            ("mode", "TEXT DEFAULT 'auto'"),
            ("oom_retries", "INTEGER DEFAULT 0")
        ]
        for col_name, col_type in new_cols:
            if col_name not in columns:
                try:
                    await db.execute(f"ALTER TABLE generations ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        await db.commit()
    app_logger.info(f"Database initialized at {DB_PATH}")

async def insert_generation(data: Dict[str, Any]) -> str:
    fields = [
        "id", "created_at", "prompt", "enhanced_prompt", "negative_prompt",
        "model", "model_version", "loras", "seed", "steps", "guidance",
        "sampler", "scheduler", "style", "aspect_ratio", "quality", "mode", "oom_retries",
        "width", "height", "generation_time",
        "peak_vram_mb", "vram_strategy", "gpu_name", "image_path",
        "thumbnail_path", "is_favorite", "rating", "tags"
    ]
    placeholders = ", ".join([f":{f}" for f in fields])
    names = ", ".join(fields)
    sql = f"INSERT OR REPLACE INTO generations ({names}) VALUES ({placeholders})"

    payload = dict(data)
    if isinstance(payload.get("loras"), (list, dict)):
        payload["loras"] = json.dumps(payload["loras"])
    if isinstance(payload.get("tags"), (list, dict)):
        payload["tags"] = json.dumps(payload["tags"])

    for field in fields:
        if field not in payload or payload[field] is None:
            if field in ["enhanced_prompt", "negative_prompt", "sampler", "scheduler", "style", "aspect_ratio", "quality", "mode", "thumbnail_path", "model_version", "vram_strategy", "gpu_name"]:
                payload[field] = ""
            elif field in ["seed", "steps", "width", "height", "oom_retries", "is_favorite", "rating"]:
                payload[field] = 0
            elif field in ["guidance", "generation_time", "peak_vram_mb"]:
                payload[field] = 0.0
            elif field in ["tags", "loras"]:
                payload[field] = "[]"
            else:
                payload[field] = ""

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, payload)
        await db.commit()

    return payload["id"]

async def list_generations(
    limit: int = 50,
    offset: int = 0,
    favorite_only: bool = False,
    model_filter: Optional[str] = None,
    search_query: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    conditions = []
    params = []

    if favorite_only:
        conditions.append("is_favorite = 1")
    if model_filter:
        conditions.append("model = ?")
        params.append(model_filter)
    if search_query:
        conditions.append("(prompt LIKE ? OR enhanced_prompt LIKE ?)")
        search_like = f"%{search_query}%"
        params.extend([search_like, search_like])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_sql = f"SELECT COUNT(*) FROM generations {where_clause}"
    query_sql = f"""
        SELECT * FROM generations {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(count_sql, params) as cursor:
            total_count = (await cursor.fetchone())[0]

        query_params = list(params) + [limit, offset]
        async with db.execute(query_sql, query_params) as cursor:
            rows = await cursor.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if isinstance(d.get("loras"), str):
                    try:
                        d["loras"] = json.loads(d["loras"])
                    except Exception:
                        d["loras"] = []
                results.append(d)

    return results, total_count

async def toggle_favorite(generation_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_favorite FROM generations WHERE id = ?", (generation_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            new_val = 1 if row[0] == 0 else 0

        await db.execute("UPDATE generations SET is_favorite = ? WHERE id = ?", (new_val, generation_id))
        await db.commit()
    return bool(new_val)

async def delete_generation(generation_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT image_path, thumbnail_path FROM generations WHERE id = ?", (generation_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                img_p = Path(row[0])
                if img_p.exists():
                    try:
                        img_p.unlink()
                    except Exception as e:
                        app_logger.warning(f"Could not delete image file {img_p}: {e}")
                if row[1]:
                    thumb_p = Path(row[1])
                    if thumb_p.exists():
                        try:
                            thumb_p.unlink()
                        except Exception:
                            pass

        await db.execute("DELETE FROM generations WHERE id = ?", (generation_id,))
        await db.commit()
    return True

async def get_generation_by_id(generation_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM generations WHERE id = ?", (generation_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if isinstance(d.get("loras"), str):
                try:
                    d["loras"] = json.loads(d["loras"])
                except Exception:
                    d["loras"] = []
            return d
