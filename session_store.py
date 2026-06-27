"""
memory/session_store.py
───────────────────────
In-memory session store with optional JSON file persistence.
Sessions survive server restarts when SESSIONS_DIR is set.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

SESSIONS_DIR = os.getenv("SESSIONS_DIR", "./sessions")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))


class SessionStore:
    def __init__(self):
        self._cache: dict = {}
        self._dir = Path(SESSIONS_DIR)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_or_create(self, session_id: str) -> dict:
        if session_id not in self._cache:
            existing = self._load_file(session_id)
            if existing:
                self._cache[session_id] = existing
            else:
                self._cache[session_id] = self._new_session(session_id)
        return self._cache[session_id]

    def get(self, session_id: str) -> Optional[dict]:
        if session_id in self._cache:
            return self._cache[session_id]
        return self._load_file(session_id)

    def save(self, session_id: str, session: dict) -> None:
        session["updated_at"] = time.time()
        self._cache[session_id] = session
        self._save_file(session_id, session)

    def delete(self, session_id: str) -> bool:
        found = session_id in self._cache
        self._cache.pop(session_id, None)
        path = self._path(session_id)
        if path.exists():
            path.unlink()
            found = True
        return found

    def list_sessions(self) -> list[str]:
        return list(self._cache.keys())

    # ── Internals ─────────────────────────────────────────────────────────────

    def _new_session(self, session_id: str) -> dict:
        return {
            "session_id": session_id,
            "history": [],
            "topics": [],
            "turn": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }

    def _path(self, session_id: str) -> Path:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        return self._dir / f"{safe_id}.json"

    def _save_file(self, session_id: str, session: dict) -> None:
        try:
            with open(self._path(session_id), "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Could not persist session {session_id}: {e}")

    def _load_file(self, session_id: str) -> Optional[dict]:
        path = self._path(session_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # TTL check
            age_hours = (time.time() - data.get("updated_at", 0)) / 3600
            if age_hours > SESSION_TTL_HOURS:
                path.unlink()
                return None
            return data
        except Exception as e:
            log.warning(f"Could not load session file {path}: {e}")
            return None

    def _load_from_disk(self) -> None:
        """Load non-expired sessions into cache on startup."""
        loaded = 0
        for path in self._dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                age_hours = (time.time() - data.get("updated_at", 0)) / 3600
                if age_hours <= SESSION_TTL_HOURS:
                    self._cache[data["session_id"]] = data
                    loaded += 1
                else:
                    path.unlink()
            except Exception:
                pass
        log.info(f"SessionStore: loaded {loaded} sessions from disk")