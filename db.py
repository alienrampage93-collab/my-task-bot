"""
Shared SQLite database layer for the Advertiser Bot and Worker Bot.
Both bots import this module and talk to the same shared.db file.
WAL mode is enabled so two separate processes can read/write concurrently.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "shared.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                ad_id           INTEGER PRIMARY KEY AUTOINCREMENT,
                link            TEXT NOT NULL,
                channel_id      INTEGER,
                channel_title   TEXT,
                advertiser_id   INTEGER NOT NULL,
                target_joins    INTEGER NOT NULL DEFAULT 100,
                current_joins   INTEGER NOT NULL DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'pending'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                points  INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                ad_id   INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (ad_id, user_id)
            )
        """)
        conn.commit()


# ---------------------------------------------------------------- ads ----

def create_pending_ad(link, channel_id, channel_title, advertiser_id, target_joins=100):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO ads (link, channel_id, channel_title, advertiser_id, target_joins) "
            "VALUES (?, ?, ?, ?, ?)",
            (link, channel_id, channel_title, advertiser_id, target_joins),
        )
        conn.commit()
        return cur.lastrowid


def get_ad(ad_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM ads WHERE ad_id = ?", (ad_id,)).fetchone()
        return dict(row) if row else None


def approve_ad(ad_id):
    with get_conn() as conn:
        conn.execute("UPDATE ads SET status = 'active' WHERE ad_id = ?", (ad_id,))
        conn.commit()


def reject_ad(ad_id):
    with get_conn() as conn:
        conn.execute("UPDATE ads SET status = 'rejected' WHERE ad_id = ?", (ad_id,))
        conn.commit()


def get_active_ads():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ads WHERE status = 'active' AND current_joins < target_joins "
            "ORDER BY ad_id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# -------------------------------------------------------------- users ----

def ensure_user(user_id):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 0)", (user_id,))
        conn.commit()


def get_user_points(user_id):
    ensure_user(user_id)
    with get_conn() as conn:
        row = conn.execute("SELECT points FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return row["points"] if row else 0


# ------------------------------------------------------- verifications ----

def has_verified(ad_id, user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM verifications WHERE ad_id = ? AND user_id = ?", (ad_id, user_id)
        ).fetchone()
        return row is not None


def record_verification(ad_id, user_id, points=50):
    """
    Atomically: check for duplicates, credit points, bump current_joins,
    and auto-complete the ad once target_joins is reached.
    Returns (success: bool, reason: str)
    """
    ensure_user(user_id)
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM verifications WHERE ad_id = ? AND user_id = ?", (ad_id, user_id)
        ).fetchone()
        if existing:
            return False, "already_claimed"

        ad = conn.execute("SELECT * FROM ads WHERE ad_id = ?", (ad_id,)).fetchone()
        if not ad or ad["status"] != "active":
            return False, "not_active"

        conn.execute("INSERT INTO verifications (ad_id, user_id) VALUES (?, ?)", (ad_id, user_id))
        conn.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))

        new_joins = ad["current_joins"] + 1
        if new_joins >= ad["target_joins"]:
            conn.execute(
                "UPDATE ads SET current_joins = ?, status = 'completed' WHERE ad_id = ?",
                (new_joins, ad_id),
            )
        else:
            conn.execute("UPDATE ads SET current_joins = ? WHERE ad_id = ?", (new_joins, ad_id))

        conn.commit()
        return True, "ok"
