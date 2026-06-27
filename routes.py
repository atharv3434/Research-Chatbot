"""
api/routes.py — Route handlers for the Research Chatbot API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from memory.session_store import SessionStore
from memory.context_manager import ContextManager
from utils.claude_client import ClaudeClient
from utils.topic_extractor import extract_topics

router = APIRouter()
store = SessionStore()
claude = ClaudeClient()
context_mgr = ContextManager()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    stream: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    topics: list[str]
    turn: int
    context_tokens: int


class ClearResponse(BaseModel):
    session_id: str
    cleared: bool


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """
    Send a message and receive a research-assistant reply.
    Creates a new session if session_id is not provided.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(body.message) > 4000:
        raise HTTPException(status_code=400, detail="Message too long (max 4000 chars).")

    # Resolve or create session
    session_id = body.session_id or str(uuid.uuid4())
    session = store.get_or_create(session_id)

    # Add user message to history
    session["history"].append({"role": "user", "content": body.message})

    # Prune history to fit context window
    pruned_history = context_mgr.prune(session["history"])

    # Call Claude
    reply = await claude.complete(messages=pruned_history)

    # Persist assistant reply
    session["history"].append({"role": "assistant", "content": reply})

    # Extract and accumulate topics
    new_topics = extract_topics(body.message + " " + reply)
    session["topics"] = list(set(session.get("topics", [])) | new_topics)
    session["turn"] = session.get("turn", 0) + 1

    store.save(session_id, session)

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        topics=session["topics"],
        turn=session["turn"],
        context_tokens=context_mgr.count_tokens(pruned_history),
    )


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Return full history for a session."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "history": session["history"],
        "topics": session.get("topics", []),
        "turn": session.get("turn", 0),
    }


@router.delete("/sessions/{session_id}", response_model=ClearResponse)
def clear_session(session_id: str):
    """Delete a session and its history."""
    deleted = store.delete(session_id)
    return ClearResponse(session_id=session_id, cleared=deleted)


@router.get("/sessions/{session_id}/topics")
def get_topics(session_id: str):
    """Return the research topics extracted from a session."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "topics": session.get("topics", [])}


@router.get("/sessions/{session_id}/export")
def export_session(session_id: str):
    """Export session as plain text."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    lines = []
    for msg in session["history"]:
        role = "You" if msg["role"] == "user" else "Assistant"
        lines.append(f"[{role}]\n{msg['content']}")
    return {"session_id": session_id, "text": "\n\n---\n\n".join(lines)}