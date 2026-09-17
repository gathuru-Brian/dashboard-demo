import sqlite3
from pathlib import Path

# Database file
DB_PATH = Path(__file__).parent / "users.db"


def get_connection():
    """
    Create and return a SQLite connection.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """
    Create all required tables.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        fullname TEXT NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        role TEXT NOT NULL,

        department TEXT,

        status TEXT DEFAULT 'Active',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        last_login TIMESTAMP

    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")