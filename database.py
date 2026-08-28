import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Migration: add the username column to any pre-existing users table.
    # Legacy rows keep NULL username; case-insensitive uniqueness is enforced
    # via an index (NULLs are treated as distinct, so old rows don't collide).
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_idx "
        "ON users (LOWER(username))"
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            synthesis TEXT,
            paper_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Shared, cross-user cache keyed by the normalized (preprocessed, lowercased) topic.
    # Lets us skip the expensive pipeline (3 Claude calls) when the same topic was
    # searched recently by anyone.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            id SERIAL PRIMARY KEY,
            topic TEXT UNIQUE NOT NULL,
            synthesis TEXT NOT NULL,
            paper_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully")


def create_user(email, password_hash, username=None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, username) VALUES (%s, %s, %s)",
            (email, password_hash, username)
        )
        conn.commit()
        cursor.execute(
            "SELECT * FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()
        return dict(user)
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = %s", (email,)
        )
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def get_user_by_username(username):
    """Case-insensitive lookup so usernames are unique regardless of casing."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(%s)", (username,)
        )
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def update_username(user_id, username):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET username = %s WHERE id = %s", (username, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def update_password(user_id, password_hash):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id):
    """Delete a user and their search history (history has a FK to users)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM search_history WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def save_search(user_id, topic, synthesis, paper_count):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO search_history (user_id, topic, synthesis, paper_count) VALUES (%s, %s, %s, %s)",
            (user_id, topic, synthesis, paper_count)
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_search(topic, max_age_days=7):
    """Return a cached synthesis for this normalized topic if one exists and is
    fresher than max_age_days, otherwise None. Keeps academic results reasonably
    current while still avoiding repeat pipeline runs."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT synthesis, paper_count FROM search_cache
            WHERE topic = %s
              AND created_at > NOW() - (%s || ' days')::interval
            """,
            (topic, max_age_days)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_to_cache(topic, synthesis, paper_count):
    """Upsert a cache entry, refreshing the stored synthesis and timestamp."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO search_cache (topic, synthesis, paper_count)
            VALUES (%s, %s, %s)
            ON CONFLICT (topic)
            DO UPDATE SET synthesis = EXCLUDED.synthesis,
                          paper_count = EXCLUDED.paper_count,
                          created_at = NOW()
            """,
            (topic, synthesis, paper_count)
        )
        conn.commit()
    finally:
        conn.close()


def get_user_history(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM search_history WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()