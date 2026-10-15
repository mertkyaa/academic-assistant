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
    """Create the only table the app still needs.

    Accounts were removed — search is open and rate-limited per IP — so there is
    no users or search_history table here any more. Existing deployments keep
    those tables untouched (nothing reads or writes them); drop them by hand if
    and when you want the space back.
    """
    conn = get_connection()
    cursor = conn.cursor()

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


if __name__ == "__main__":
    init_db()
