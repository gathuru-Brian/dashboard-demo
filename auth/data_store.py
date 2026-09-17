"""
Upload persistence
RMIP-DSS
---------------------------------
Stores every dataset a user loads (portfolio file, internal claims file,
remote URL, or Kaggle download) to disk, with metadata recorded in the
database. This lets the admin console monitor what's been uploaded across
all users, not just what's sitting in a single browser's session state.

Actual data files are stored under data/uploads/<upload_id>.csv. Only
metadata (who, when, what, how many rows/columns) lives in the database --
the files themselves stay on disk to keep the database small.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from auth.authentication import get_connection

ROOT = Path(__file__).resolve().parents[1]
UPLOADS_DIR = ROOT / "data" / "uploads"


def initialize_uploads_table() -> None:
    """
    Creates the uploads metadata table if it doesn't exist. Safe to call on
    every app startup, same pattern as initialize_database().
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS uploads(

            id TEXT PRIMARY KEY,

            uploader_email TEXT,

            uploader_name TEXT,

            source TEXT NOT NULL,

            original_filename TEXT,

            stored_path TEXT NOT NULL,

            row_count INTEGER,

            column_count INTEGER,

            columns TEXT,

            uploaded_at TEXT NOT NULL

        )
        """
    )
    conn.commit()
    conn.close()


def save_upload(
    uploader_email: str,
    uploader_name: str,
    df: pd.DataFrame,
    source: str,
    original_filename: str = "",
) -> str:
    """
    Persists an uploaded DataFrame to disk and records its metadata.

    source: a short label identifying where this came from, e.g.
        "portfolio_file", "internal_claims", "remote_url", "kaggle".

    Returns the generated upload_id.
    """
    initialize_uploads_table()

    upload_id = uuid.uuid4().hex
    stored_path = UPLOADS_DIR / f"{upload_id}.csv"
    df.to_csv(stored_path, index=False)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO uploads(
            id, uploader_email, uploader_name, source, original_filename,
            stored_path, row_count, column_count, columns, uploaded_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            upload_id,
            uploader_email,
            uploader_name,
            source,
            original_filename,
            str(stored_path),
            len(df),
            len(df.columns),
            ",".join(str(c) for c in df.columns),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()
    return upload_id


def list_uploads(limit: int = 200):
    """
    Returns the most recent upload records, newest first, for the admin
    console's monitoring view.
    """
    initialize_uploads_table()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, uploader_email, uploader_name, source, original_filename,
               stored_path, row_count, column_count, columns, uploaded_at
        FROM uploads
        ORDER BY uploaded_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_upload_dataframe(upload_id: str) -> pd.DataFrame | None:
    """
    Loads a previously-persisted upload back into a DataFrame, for the
    admin to preview or download. Returns None if the record or file is
    missing.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stored_path FROM uploads WHERE id=?", (upload_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    path = Path(row["stored_path"])
    if not path.exists():
        return None
    return pd.read_csv(path)


def delete_upload(upload_id: str) -> bool:
    """
    Deletes an upload's stored file and its metadata record. Returns True
    if something was actually deleted.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT stored_path FROM uploads WHERE id=?", (upload_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False

    path = Path(row["stored_path"])
    if path.exists():
        path.unlink()

    cursor.execute("DELETE FROM uploads WHERE id=?", (upload_id,))
    conn.commit()
    conn.close()
    return True


def total_upload_storage_bytes() -> int:
    """Returns the total size, in bytes, of all files under data/uploads/."""
    if not UPLOADS_DIR.exists():
        return 0
    return sum(f.stat().st_size for f in UPLOADS_DIR.glob("*.csv") if f.is_file())


def delete_uploads_older_than(days: int) -> int:
    """
    Deletes every upload (file + metadata record) older than the given
    number of days. Returns the count of uploads deleted.

    Intended to be run periodically (e.g. from a scheduled task, or a
    manual "Clean up old uploads" button in the admin console) to enforce
    a data retention policy rather than letting uploads accumulate forever.
    """
    initialize_uploads_table()
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, stored_path FROM uploads WHERE uploaded_at < ?", (cutoff_str,))
    old_uploads = cursor.fetchall()
    conn.close()

    deleted_count = 0
    for record in old_uploads:
        if delete_upload(record["id"]):
            deleted_count += 1
    return deleted_count