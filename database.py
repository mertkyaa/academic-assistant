import sqlite3

DATABASE = "academic.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            synthesis TEXT,
            paper_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully")


def create_user(email, password_hash):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        cursor = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        )
        user = cursor.fetchone()
        return dict(user)
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        )
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def save_search(user_id, topic, synthesis, paper_count):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO search_history (user_id, topic, synthesis, paper_count) VALUES (?, ?, ?, ?)",
            (user_id, topic, synthesis, paper_count)
        )
        conn.commit()
    finally:
        conn.close()


def get_user_history(user_id):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM search_history WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()