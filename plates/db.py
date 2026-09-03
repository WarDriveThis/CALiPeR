import sqlite3
import datetime
from config import DB_PATH, PLATE_POOL_MAX


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_text TEXT NOT NULL,
            confidence REAL,
            first_seen TEXT,
            last_seen TEXT,
            seen_count INTEGER DEFAULT 1,
            latest_image TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plate ON plates(plate_text)")
    conn.commit()
    conn.close()


def upsert_plate(plate_text, confidence, image_filename):
    now  = datetime.datetime.now().isoformat()
    conn = get_conn()
    existing = conn.execute(
        "SELECT id, seen_count FROM plates WHERE plate_text = ?",
        (plate_text,)
    ).fetchone()
    if existing:
        conn.execute("""
            UPDATE plates SET last_seen=?, seen_count=seen_count+1,
            confidence=?, latest_image=? WHERE plate_text=?
        """, (now, confidence, image_filename, plate_text))
    else:
        conn.execute("""
            INSERT INTO plates (plate_text, confidence, first_seen, last_seen, latest_image)
            VALUES (?, ?, ?, ?, ?)
        """, (plate_text, confidence, now, now, image_filename))
        # Prune oldest if over pool max
        conn.execute("""
            DELETE FROM plates WHERE id IN (
                SELECT id FROM plates ORDER BY last_seen ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM plates) - ?)
            )
        """, (PLATE_POOL_MAX,))
    conn.commit()
    conn.close()


def expire_plates(max_age_seconds: int):
    """
    Remove plates whose last_seen is older than max_age_seconds.
    Called periodically by the display thread.
    Returns count of plates removed.
    """
    if max_age_seconds <= 0:
        return 0
    cutoff = (datetime.datetime.now() -
              datetime.timedelta(seconds=max_age_seconds)).isoformat()
    conn   = get_conn()
    cur    = conn.execute(
        "DELETE FROM plates WHERE last_seen < ?", (cutoff,)
    )
    removed = cur.rowcount
    conn.commit()
    conn.close()
    return removed


def get_all_plates():
    conn = get_conn()
    rows = conn.execute("""
        SELECT plate_text, confidence, first_seen, last_seen,
               seen_count, latest_image
        FROM plates ORDER BY last_seen DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_plate_texts() -> list:
    """Return just the plate_text values — lightweight pool snapshot for display."""
    conn = get_conn()
    rows = conn.execute("SELECT plate_text FROM plates").fetchall()
    conn.close()
    return [r["plate_text"] for r in rows]


def get_latest_plate():
    conn = get_conn()
    row  = conn.execute("""
        SELECT * FROM plates ORDER BY last_seen DESC LIMIT 1
    """).fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats():
    conn = get_conn()
    row  = conn.execute("""
        SELECT COUNT(*) as total,
               COUNT(DISTINCT plate_text) as unique_plates
        FROM plates
    """).fetchone()
    conn.close()
    return dict(row)


def clear_pool():
    conn = get_conn()
    conn.execute("DELETE FROM plates")
    conn.commit()
    conn.close()


def delete_plate(plate_text: str):
    """Remove a single plate entry by plate_text."""
    conn = get_conn()
    conn.execute("DELETE FROM plates WHERE plate_text = ?", (plate_text,))
    conn.commit()
    conn.close()


def add_plate(plate_text: str, confidence: float = 1.0):
    """Manually insert a plate string into the pool."""
    plate_text = plate_text.strip().upper()
    if not plate_text:
        return False
    upsert_plate(plate_text, confidence, None)
    return True
