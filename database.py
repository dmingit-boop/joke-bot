import sqlite3
from config import DB_PATH


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                subscribed INTEGER DEFAULT 1,
                mood TEXT DEFAULT 'обычный'
            );
            CREATE TABLE IF NOT EXISTS jokes (
                joke_id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                source TEXT DEFAULT 'user',
                theme TEXT DEFAULT 'general',
                date_added TEXT DEFAULT (date('now'))
            );
            CREATE TABLE IF NOT EXISTS ratings (
                user_id INTEGER,
                joke_id INTEGER,
                rating INTEGER,
                PRIMARY KEY (user_id, joke_id)
            );
            CREATE TABLE IF NOT EXISTS seen (
                user_id INTEGER,
                joke_id INTEGER,
                PRIMARY KEY (user_id, joke_id)
            );
        """)
        try:
            con.execute("ALTER TABLE users ADD COLUMN mood TEXT DEFAULT 'обычный'")
        except Exception:
            pass


def add_user(user_id: int, username: str):
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO users(user_id, username) VALUES (?, ?)",
            (user_id, username),
        )


def set_subscribe(user_id: int, status: bool):
    with _conn() as con:
        con.execute(
            "UPDATE users SET subscribed = ? WHERE user_id = ?",
            (1 if status else 0, user_id),
        )


def get_subscribed_users() -> list:
    with _conn() as con:
        rows = con.execute(
            "SELECT user_id FROM users WHERE subscribed = 1"
        ).fetchall()
    return [r[0] for r in rows]


def add_joke(text: str, source: str = "user", theme: str = "general") -> int:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO jokes(text, source, theme) VALUES (?, ?, ?)",
            (text, source, theme),
        )
    return cur.lastrowid


def mark_seen(user_id: int, joke_id: int):
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO seen(user_id, joke_id) VALUES (?, ?)",
            (user_id, joke_id),
        )


def get_random_joke(user_id: int) -> dict | None:
    with _conn() as con:
        # сначала ищем непросмотренный и не задизлайканный
        row = con.execute(
            """
            SELECT j.joke_id, j.text FROM jokes j
            WHERE j.joke_id NOT IN (
                SELECT joke_id FROM ratings WHERE user_id = ? AND rating = -1
            )
            AND j.joke_id NOT IN (
                SELECT joke_id FROM seen WHERE user_id = ?
            )
            ORDER BY RANDOM() LIMIT 1
            """,
            (user_id, user_id),
        ).fetchone()

        if not row:
            # все просмотрены — сбрасываем историю и начинаем заново
            con.execute("DELETE FROM seen WHERE user_id = ?", (user_id,))
            row = con.execute(
                """
                SELECT j.joke_id, j.text FROM jokes j
                WHERE j.joke_id NOT IN (
                    SELECT joke_id FROM ratings WHERE user_id = ? AND rating = -1
                )
                ORDER BY RANDOM() LIMIT 1
                """,
                (user_id,),
            ).fetchone()

    if row:
        mark_seen(user_id, row[0])
        return {"joke_id": row[0], "text": row[1]}
    return None


def save_rating(user_id: int, joke_id: int, rating: int):
    with _conn() as con:
        con.execute(
            """
            INSERT INTO ratings(user_id, joke_id, rating) VALUES (?, ?, ?)
            ON CONFLICT(user_id, joke_id) DO UPDATE SET rating = excluded.rating
            """,
            (user_id, joke_id, rating),
        )


def set_mood(user_id: int, mood: str):
    with _conn() as con:
        con.execute("UPDATE users SET mood = ? WHERE user_id = ?", (mood, user_id))


def get_mood(user_id: int) -> str:
    with _conn() as con:
        row = con.execute("SELECT mood FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return row[0] if row else "обычный"


def get_top_jokes(limit: int = 10) -> list:
    with _conn() as con:
        rows = con.execute(
            """
            SELECT j.joke_id, j.text, COALESCE(SUM(r.rating), 0) AS score
            FROM jokes j
            LEFT JOIN ratings r ON j.joke_id = r.joke_id
            GROUP BY j.joke_id
            ORDER BY score DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [{"joke_id": r[0], "text": r[1], "score": r[2]} for r in rows]
