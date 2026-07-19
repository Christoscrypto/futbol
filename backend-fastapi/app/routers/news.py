from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, Any

from ..db import get_db, next_id, null_if_empty, strip_mongo_id

router = APIRouter(prefix="/api/news", tags=["news"])


class NewsIn(BaseModel):
    id: Optional[int] = None
    title: str = ""
    cat: str = "Torneo"
    date: Optional[str] = None
    emoji: str = "📰"
    excerpt: str = ""


@router.get("")
async def list_news():
    db = get_db()
    col = db["news"]
    news = await col.find({}).sort([("date", -1), ("id", -1)]).to_list(length=None)
    return [strip_mongo_id(n) for n in news]


@router.post("")
async def upsert_news(payload: NewsIn):
    db = get_db()
    col = db["news"]

    title = (payload.title or "").strip()
    if title == "":
        return Response(
            content='{"error":"El título es obligatorio"}',
            status_code=400,
            media_type="application/json",
        )

    fields: dict[str, Any] = {
        "title": title,
        "cat": payload.cat or "Torneo",
        "date": null_if_empty(payload.date),
        "emoji": payload.emoji or "📰",
        "excerpt": payload.excerpt or "",
    }

    if payload.id:
        news_id = payload.id
        await col.update_one({"id": news_id}, {"$set": fields})
    else:
        news_id = await next_id(col)
        await col.insert_one({"id": news_id, **fields})

    saved = await col.find_one({"id": news_id})
    return strip_mongo_id(saved)


@router.delete("")
async def delete_news(id: Optional[int] = None):
    db = get_db()
    col = db["news"]
    if id:
        await col.delete_one({"id": id})
    return {"deleted": True}
