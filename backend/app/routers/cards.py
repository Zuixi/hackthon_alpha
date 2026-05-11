from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.user import User
from app.models.idea_card import IdeaCard
from app.auth import get_current_user
from app.schemas.card import (
    CreateCardRequest,
    UpdateCardRequest,
    CardResponse,
    CardListResponse,
)

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _card_to_response(card: IdeaCard) -> CardResponse:
    return CardResponse(
        id=card.id,
        content=card.content,
        tags=card.tags or [],
        hot_topic_id=card.hot_topic_id,
        hot_topic_title=card.hot_topic.title if card.hot_topic else None,
        chat_session_id=card.chat_session_id,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.get("", response_model=CardListResponse)
async def list_cards(
    tag: str = Query(None),
    search: str = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(IdeaCard).filter(IdeaCard.user_id == user.id)

    if tag:
        q = q.filter(IdeaCard.tags.any(tag))
    if search:
        q = q.filter(or_(IdeaCard.content.ilike(f"%{search}%")))

    total = q.count()
    cards = q.order_by(IdeaCard.created_at.desc()).offset(offset).limit(limit).all()

    return CardListResponse(
        items=[_card_to_response(c) for c in cards],
        total=total,
    )


@router.post("", response_model=CardResponse)
async def create_card(
    req: CreateCardRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = IdeaCard(
        user_id=user.id,
        content=req.content,
        tags=req.tags,
        hot_topic_id=req.hot_topic_id,
        chat_session_id=req.chat_session_id,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return _card_to_response(card)


@router.get("/tags", response_model=list[str])
async def list_tags(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all unique tags for the current user."""
    cards = db.query(IdeaCard.tags).filter(IdeaCard.user_id == user.id).all()
    all_tags = set()
    for (tags,) in cards:
        if tags:
            all_tags.update(tags)
    return sorted(all_tags)


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = (
        db.query(IdeaCard)
        .filter(IdeaCard.id == card_id, IdeaCard.user_id == user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card_to_response(card)


@router.put("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: str,
    req: UpdateCardRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = (
        db.query(IdeaCard)
        .filter(IdeaCard.id == card_id, IdeaCard.user_id == user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if req.content is not None:
        card.content = req.content
    if req.tags is not None:
        card.tags = req.tags

    db.commit()
    db.refresh(card)
    return _card_to_response(card)


@router.delete("/{card_id}")
async def delete_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = (
        db.query(IdeaCard)
        .filter(IdeaCard.id == card_id, IdeaCard.user_id == user.id)
        .first()
    )
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
    return {"ok": True}
