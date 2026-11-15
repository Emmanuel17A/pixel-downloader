import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser("~/.pixel-downloader/downloads.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            filename TEXT NOT NULL,
            save_path TEXT NOT NULL,
            total_size INTEGER DEFAULT 0,
            downloaded INTEGER DEFAULT 0,
            status TEXT DEFAULT 'queued',
            segments INTEGER DEFAULT 8,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT
        )
    ''')
    conn.commit()

    # Fix any downloads that were interrupted mid-session
    c.execute('''
        UPDATE downloads
        SET status = 'failed'
        WHERE status IN ('downloading', 'queued')
    ''')

    # Fix stuck "Fetching title..." entries
    c.execute('''
        UPDATE downloads
        SET status = 'failed', filename = 'Download failed — retry'
        WHERE filename IN ('Fetching title...', 'watch', '')
        AND status != 'completed'
    ''')

    conn.commit()
    conn.close()

def add_download(url, filename, save_path, total_size=0, segments=8):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO downloads (url, filename, save_path, total_size, segments)
        VALUES (?, ?, ?, ?, ?)
    ''', (url, filename, save_path, total_size, segments))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id

def update_download(download_id, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fields = ', '.join([f"{k} = ?" for k in kwargs])
    values = list(kwargs.values()) + [download_id]
    c.execute(f"UPDATE downloads SET {fields} WHERE id = ?", values)
    conn.commit()
    conn.close()

def get_all_downloads():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM downloads ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_download(download_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_download(download_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
    conn.commit()
    conn.close()
