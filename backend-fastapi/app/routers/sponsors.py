from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, Any

from ..db import get_db, next_id, strip_mongo_id

router = APIRouter(prefix="/api/sponsors", tags=["sponsors"])

# Mismo orden que FIELD(tier,'Platino','Oro','Plata','Bronce') en el SQL original
TIER_ORDER = {"Platino": 0, "Oro": 1, "Plata": 2, "Bronce": 3}


class SponsorIn(BaseModel):
    id: Optional[int] = None
    name: str = ""
    tier: str = "Bronce"
    emoji: str = "🏢"
    img: Optional[str] = None


@router.get("")
async def list_sponsors():
    db = get_db()
    col = db["sponsors"]
    sponsors = await col.find({}).to_list(length=None)
    sponsors.sort(key=lambda s: (TIER_ORDER.get(s.get("tier"), 99), s.get("id", 0)))
    return [strip_mongo_id(s) for s in sponsors]


@router.post("")
async def upsert_sponsor(payload: SponsorIn):
    db = get_db()
    col = db["sponsors"]

    name = (payload.name or "").strip()
    if name == "":
        return Response(
            content='{"error":"El nombre es obligatorio"}',
            status_code=400,
            media_type="application/json",
        )

    fields: dict[str, Any] = {
        "name": name,
        "tier": payload.tier or "Bronce",
        "emoji": payload.emoji or "🏢",
        "img": payload.img or None,
    }

    if payload.id:
        sponsor_id = payload.id
        await col.update_one({"id": sponsor_id}, {"$set": fields})
    else:
        sponsor_id = await next_id(col)
        await col.insert_one({"id": sponsor_id, **fields})

    saved = await col.find_one({"id": sponsor_id})
    return strip_mongo_id(saved)


@router.delete("")
async def delete_sponsor(id: Optional[int] = None):
    db = get_db()
    col = db["sponsors"]
    if id:
        await col.delete_one({"id": id})
    return {"deleted": True}
