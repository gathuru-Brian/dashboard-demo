import sqlite3

conn = sqlite3.connect("database/users.db")
cursor = conn.cursor()

columns = [
    ("department", "TEXT"),
    ("status", "TEXT DEFAULT 'Approved'"),
    ("created_at", "TEXT"),
    ("last_login", "TEXT")
]

for column_name, column_type in columns:
    try:
        cursor.execute(
            f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
        )
        print(f"Added column: {column_name}")
    except sqlite3.OperationalError:
        print(f"Column already exists: {column_name}")

conn.commit()
conn.close()

print("Database updated successfully.")