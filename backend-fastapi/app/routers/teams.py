from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, Any

from ..db import get_db, next_id, strip_mongo_id

router = APIRouter(prefix="/api/teams", tags=["teams"])


class TeamIn(BaseModel):
    id: Optional[int] = None
    name: str = ""
    short: str = ""
    city: str = ""
    cat: str = "Premier"
    grupo: str = "A"
    emoji: str = "⚽"
    img: Optional[str] = None
    color1: Optional[str] = "#0066FF"
    color2: Optional[str] = "#FFD700"


@router.get("")
async def list_teams():
    db = get_db()
    col = db["teams"]
    teams = await col.find({}, {"_id": 0}).sort("id", 1).to_list(length=None)
    return teams


@router.post("")
async def upsert_team(payload: TeamIn):
    db = get_db()
    col = db["teams"]

    name = (payload.name or "").strip()
    if name == "":
        return Response(
            content='{"error":"El nombre es obligatorio"}',
            status_code=400,
            media_type="application/json",
        )

    fields: dict[str, Any] = {
        "name": name,
        "short": (payload.short or "").strip(),
        "city": (payload.city or "").strip(),
        "cat": payload.cat or "Premier",
        "grupo": payload.grupo or "A",
        "emoji": payload.emoji or "⚽",
        "img": payload.img or None,
        "color1": payload.color1 or "#0066FF",
        "color2": payload.color2 or "#FFD700",
    }

    if payload.id:
        team_id = payload.id
        await col.update_one({"id": team_id}, {"$set": fields})
    else:
        team_id = await next_id(col)
        await col.insert_one(
            {
                "id": team_id,
                **fields,
                "pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0,
            }
        )

    saved = await col.find_one({"id": team_id}, {"_id": 0})
    return saved


@router.delete("")
async def delete_team(id: Optional[int] = None):
    db = get_db()
    col = db["teams"]

    if id:
        await col.delete_one({"id": id})
        # Igual que ON DELETE SET NULL en players.team_id
        await db["players"].update_many({"team_id": id}, {"$set": {"team_id": None}})
        # Igual que ON DELETE CASCADE en matches
        await db["matches"].delete_many({"$or": [{"local": id}, {"visit": id}]})

    return {"deleted": True}
