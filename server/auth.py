"""Google identity verification and revocable, opaque INDRA sessions."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import secrets
import sqlite3
import time
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
SESSION_TTL_SECONDS = 7 * 24 * 3600


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


class AuthStore:
    """SQLite user/session store; only a hash of each bearer token is persisted."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self.init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=5)

    def init_db(self):
        with self._connect() as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL, picture TEXT, provider TEXT NOT NULL,
                created_at TEXT NOT NULL, last_login TEXT NOT NULL)""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
            if columns and "token_hash" not in columns:
                # Old prototype sessions are revoked during the schema migration.
                conn.execute("DROP TABLE sessions")
                columns = set()
            if not columns:
                conn.execute("""CREATE TABLE sessions (
                    token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    expires_at INTEGER NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
            conn.execute("CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)")

    def upsert_user(self, user_info: dict[str, Any]) -> dict[str, Any]:
        subject, email = user_info.get("id"), user_info.get("email")
        if not isinstance(subject, str) or not subject or not isinstance(email, str) or "@" not in email:
            raise ValueError("Verified identity must include a subject and email")
        name = user_info.get("name") or email.split("@", 1)[0]
        picture = user_info.get("picture") or ""
        provider = user_info.get("provider")
        if provider not in {"google", "demo"}:
            raise ValueError("Unsupported identity provider")
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute("""INSERT INTO users
                (id,email,name,picture,provider,created_at,last_login)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(email) DO UPDATE SET name=excluded.name,
                picture=excluded.picture,last_login=excluded.last_login""",
                (subject, email.lower(), name, picture, provider, now, now))
            row = conn.execute("SELECT id,email,name,picture,provider,created_at,last_login FROM users WHERE email=?", (email.lower(),)).fetchone()
        return dict(id=row[0], email=row[1], name=row[2], picture=row[3],
                    provider=row[4], createdAt=row[5], lastLogin=row[6])

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with self._connect() as conn:
            conn.execute("INSERT INTO sessions VALUES (?,?,?,?)",
                         (_token_hash(token), user_id, now + SESSION_TTL_SECONDS,
                          datetime.now(timezone.utc).isoformat()))
            conn.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        return token

    def get_user_by_token(self, token: str) -> dict[str, Any] | None:
        if not isinstance(token, str) or not 20 <= len(token) <= 200:
            return None
        with self._connect() as conn:
            row = conn.execute("""SELECT u.id,u.email,u.name,u.picture,u.provider,
                u.created_at,u.last_login FROM sessions s JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>?""",
                (_token_hash(token), int(time.time()))).fetchone()
        if not row:
            return None
        return dict(id=row[0], email=row[1], name=row[2], picture=row[3],
                    provider=row[4], createdAt=row[5], lastLogin=row[6])

    def delete_session(self, token: str) -> bool:
        if not isinstance(token, str) or not 20 <= len(token) <= 200:
            return False
        with self._connect() as conn:
            result = conn.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
            return result.rowcount > 0


def verify_google_credential(credential: str, client_id: str | None = None) -> dict[str, Any]:
    """Verify Google ID token claims, failing closed without the configured audience."""
    audience = (client_id or GOOGLE_CLIENT_ID).strip()
    if not audience:
        raise ValueError("Google sign-in is not configured")
    if not isinstance(credential, str) or not credential or len(credential) > 8192:
        raise ValueError("Invalid Google credential")
    try:
        response = httpx.get("https://oauth2.googleapis.com/tokeninfo",
                             params={"id_token": credential}, timeout=6.0)
    except httpx.RequestError as exc:
        raise ValueError("Unable to reach Google identity verification") from exc
    if response.status_code != 200:
        raise ValueError("Google credential was rejected")
    try:
        claims = response.json()
        expiry = int(claims.get("exp", 0))
    except (ValueError, TypeError):
        raise ValueError("Google returned invalid identity claims") from None
    if claims.get("aud") != audience:
        raise ValueError("Google credential audience does not match this application")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise ValueError("Google credential issuer is invalid")
    if expiry <= int(time.time()):
        raise ValueError("Google credential has expired")
    if claims.get("email_verified") is not True:
        raise ValueError("Google account email is not verified")
    if not claims.get("sub") or not claims.get("email"):
        raise ValueError("Google credential lacks required identity claims")
    return {"id": claims["sub"], "email": claims["email"],
            "name": claims.get("name") or claims["email"].split("@", 1)[0],
            "picture": claims.get("picture", ""), "provider": "google"}


class GoogleAuthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential: str = Field(min_length=1, max_length=8192)


class DemoAuthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Demo identity is fixed server-side; clients cannot impersonate arbitrary users.
    pass
