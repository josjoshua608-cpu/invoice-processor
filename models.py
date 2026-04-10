"""
models.py
---------
Database models for user authentication.
Uses SQLite (via sqlite3 stdlib) — zero extra dependencies for local dev.
Swap the DB_PATH or engine for PostgreSQL/MySQL in production.

Future API integration: Replace with SQLAlchemy ORM + Alembic migrations.
"""

import sqlite3
import hashlib
import os
import secrets
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _hash_password(password: str, salt: str) -> str:
    """SHA-256 hash with salt. Use bcrypt/argon2 in production."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    UNIQUE NOT NULL,
            email       TEXT    UNIQUE NOT NULL,
            password_hash TEXT  NOT NULL,
            salt        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            is_active   INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token       TEXT PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def create_user(username: str, email: str, password: str) -> dict:
    """
    Register a new user.
    Returns dict with user info on success.
    Raises ValueError on duplicate username/email.
    """
    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, email, password_hash, salt, created_at) VALUES (?,?,?,?,?)",
            (username.strip(), email.strip().lower(), password_hash, salt, now),
        )
        conn.commit()
        user_id = c.lastrowid
        return {"id": user_id, "username": username, "email": email}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            raise ValueError("Username already exists.")
        raise ValueError("Email already registered.")
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Verify credentials.
    Returns user dict on success, None on failure.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, username, email, password_hash, salt FROM users WHERE username=? AND is_active=1",
            (username.strip(),),
        )
        row = c.fetchone()
        if not row:
            return None
        user_id, uname, email, stored_hash, salt = row
        if _hash_password(password, salt) == stored_hash:
            return {"id": user_id, "username": uname, "email": email}
        return None
    finally:
        conn.close()


def create_session(user_id: int) -> str:
    """Create a session token for the authenticated user."""
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?,?,?)",
        (token, user_id, now),
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: str) -> dict | None:
    """Look up a logged-in user by session token."""
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            """SELECT u.id, u.username, u.email
               FROM sessions s JOIN users u ON s.user_id = u.id
               WHERE s.token = ?""",
            (token,),
        )
        row = c.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "email": row[2]}
        return None
    finally:
        conn.close()


def delete_session(token: str):
    """Log out — remove session token."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE token=?", (token,))
    conn.commit()
    conn.close()
