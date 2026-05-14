import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.chat import ChatSession, Message
from app.models.hot_topic import HotTopic
from app.auth import get_current_user
from app.schemas.chat import (
    ChatSessionResponse,
    ChatSessionDetailResponse,
    MessageResponse,
    ChatRequest,
    CreateSessionRequest,
    UpdateSessionRequest,
)
from app.services.zhihu import zhihu_service
from app.agent.agent_loop import agent_chat_stream

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ChatSessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        resp = ChatSessionResponse(
            id=s.id,
            title=s.title,
            hot_topic_id=s.hot_topic_id,
            hot_topic_title=s.hot_topic.title if s.hot_topic else None,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=len(s.messages),
        )
        result.append(resp)
    return result


@router.post("", response_model=ChatSessionDetailResponse)
async def create_session(
    req: CreateSessionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = req.title or "新对话"
    if req.hot_topic_id:
        topic = db.query(HotTopic).filter(HotTopic.id == req.hot_topic_id).first()
        if topic:
            title = f"关于「{topic.title[:30]}」的创作"

    session = ChatSession(user_id=user.id, hot_topic_id=req.hot_topic_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)

    return ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        hot_topic_id=session.hot_topic_id,
        hot_topic_title=session.hot_topic.title if session.hot_topic else None,
        messages=[],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return ChatSessionDetailResponse(
        id=session.id,
        title=session.title,
        hot_topic_id=session.hot_topic_id,
        hot_topic_title=session.hot_topic.title if session.hot_topic else None,
        messages=[MessageResponse.model_validate(m) for m in session.messages],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.patch("/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    req: UpdateSessionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.title = req.title.strip() or session.title
    db.commit()
    db.refresh(session)
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        hot_topic_id=session.hot_topic_id,
        hot_topic_title=session.hot_topic.title if session.hot_topic else None,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/message")
async def send_message(
    session_id: str,
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message and stream AI response via SSE."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = Message(session_id=session.id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()

    history = [{"role": m.role, "content": m.content} for m in session.messages if m.role != "system"]

    topic_title = session.hot_topic.title if session.hot_topic else ""

    search_context = ""
    if topic_title:
        try:
            search_result = await zhihu_service.search_zhihu(topic_title, limit=5)
            items = search_result.get("data", search_result.get("items", []))
            if isinstance(search_result, list):
                items = search_result
            snippets = []
            for item in items[:5]:
                title = item.get("title", "")
                excerpt = item.get("excerpt", item.get("content", ""))[:200]
                if title:
                    snippets.append(f"- {title}: {excerpt}")
            search_context = "\n".join(snippets)
        except Exception as e:
            logger.warning(f"Zhihu search failed: {e}")

    async def event_stream():
        full_response: list[str] = []
        try:
            async for event in agent_chat_stream(
                user_message=req.message,
                history=history,
                topic_title=topic_title,
                search_context=search_context,
                session_id=session_id,
                user_id=user.id,
                zhihu_token=user.zhihu_token or "",
            ):
                event_type = event.get("type")

                if event_type == "text_delta":
                    chunk = event.get("content", "")
                    if chunk:
                        full_response.append(chunk)

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

        content = "".join(full_response)
        if content:
            assistant_msg = Message(session_id=session.id, role="assistant", content=content)
            db.add(assistant_msg)
            db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
