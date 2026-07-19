from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, Any

from ..db import get_db, next_id

router = APIRouter(prefix="/api/players", tags=["players"])


class PlayerIn(BaseModel):
    id: Optional[int] = None
    name: str = ""
    short: str = ""
    team: Optional[int] = None
    pos: str = "Delantero"
    num: int = 0
    emoji: str = "⚽"
    img: Optional[str] = None
    goles: int = 0
    asist: int = 0
    amarillas: int = 0
    rojas: int = 0
    nacimiento: Optional[str] = None    # fecha de nacimiento, formato YYYY-MM-DD
    nacionalidad: Optional[str] = None
    altura: Optional[int] = None        # en cm
    pie: Optional[str] = None           # "Derecho" | "Izquierdo" | "Ambidiestro"
    bio: Optional[str] = None           # biografía personalizada


def to_frontend(doc: dict | None) -> dict | None:
    """El frontend espera el campo 'team' (no 'team_id')."""
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    team_id = doc.pop("team_id", None)
    doc["team"] = team_id
    return doc


@router.get("")
async def list_players():
    db = get_db()
    col = db["players"]
    players = await col.find({}).sort("id", 1).to_list(length=None)
    return [to_frontend(p) for p in players]


@router.post("")
async def upsert_player(payload: PlayerIn):
    db = get_db()
    col = db["players"]

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
        "team_id": payload.team if payload.team else None,
        "pos": payload.pos or "Delantero",
        "num": payload.num or 0,
        "emoji": payload.emoji or "⚽",
        "img": payload.img or None,
        "goles": payload.goles or 0,
        "asist": payload.asist or 0,
        "amarillas": payload.amarillas or 0,
        "rojas": payload.rojas or 0,
        "nacimiento": payload.nacimiento or None,
        "nacionalidad": (payload.nacionalidad or "").strip() or None,
        "altura": payload.altura or None,
        "pie": payload.pie or None,
        "bio": (payload.bio or "").strip() or None,
    }

    if payload.id:
        player_id = payload.id
        await col.update_one({"id": player_id}, {"$set": fields})
    else:
        player_id = await next_id(col)
        await col.insert_one({"id": player_id, **fields})

    saved = await col.find_one({"id": player_id})
    return to_frontend(saved)


@router.delete("")
async def delete_player(id: Optional[int] = None):
    db = get_db()
    col = db["players"]
    if id:
        await col.delete_one({"id": id})
    return {"deleted": True}
