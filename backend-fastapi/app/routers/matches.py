from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, Any

from ..db import get_db, next_id, null_if_empty, strip_mongo_id

router = APIRouter(prefix="/api/matches", tags=["matches"])


class MatchEvent(BaseModel):
    tipo: str  # "Gol" | "Autogol" | "Amarilla" | "Roja" | "Asistencia"
    minuto: Optional[int] = None
    equipo: Optional[int] = None   # id del equipo (local o visitante) al que pertenece el evento
    jugador: Optional[int] = None  # id del jugador (opcional)
    nota: Optional[str] = None     # texto libre opcional (ej. "Tiro libre")


class MatchIn(BaseModel):
    id: Optional[int] = None
    fase: str = "Grupos"
    jornada: Optional[int] = None
    local: Optional[int] = None
    visit: Optional[int] = None
    gL: Optional[int] = None
    gV: Optional[int] = None
    fecha: Optional[str] = None
    hora: Optional[str] = None
    cancha: str = "Estadio Municipal"
    estado: str = "Programado"
    mvp: Optional[int] = None
    eventos: Optional[list[MatchEvent]] = None


async def recalc_standings(db):
    """
    Recalcula PJ/PG/PE/PP/GF/GC/PTS de todos los equipos a partir SOLO
    de los partidos finalizados de Fase de Grupos. Misma lógica que
    recalcStandings() en el matches.php / matches.js original.
    """
    teams_col = db["teams"]
    matches_col = db["matches"]

    await teams_col.update_many(
        {}, {"$set": {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0}}
    )

    rows = await matches_col.find(
        {
            "estado": "Finalizado",
            "$or": [{"fase": None}, {"fase": "Grupos"}, {"fase": {"$exists": False}}],
            "local": {"$ne": None},
            "visit": {"$ne": None},
            "gL": {"$ne": None},
            "gV": {"$ne": None},
        }
    ).to_list(length=None)

    stats: dict[int, dict[str, int]] = {}

    def touch(tid):
        if tid not in stats:
            stats[tid] = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0}

    for m in rows:
        l, v = m["local"], m["visit"]
        gl, gv = m["gL"], m["gV"]
        touch(l)
        touch(v)

        stats[l]["pj"] += 1
        stats[v]["pj"] += 1
        stats[l]["gf"] += gl
        stats[l]["gc"] += gv
        stats[v]["gf"] += gv
        stats[v]["gc"] += gl

        if gl > gv:
            stats[l]["pg"] += 1
            stats[l]["pts"] += 3
            stats[v]["pp"] += 1
        elif gl < gv:
            stats[v]["pg"] += 1
            stats[v]["pts"] += 3
            stats[l]["pp"] += 1
        else:
            stats[l]["pe"] += 1
            stats[l]["pts"] += 1
            stats[v]["pe"] += 1
            stats[v]["pts"] += 1

    for tid, s in stats.items():
        await teams_col.update_one({"id": tid}, {"$set": s})


@router.get("")
async def list_matches():
    db = get_db()
    col = db["matches"]
    matches = await col.find({}).sort([("fase", 1), ("jornada", 1), ("fecha", 1)]).to_list(length=None)
    return [strip_mongo_id(m) for m in matches]


@router.get("/{match_id}")
async def get_match(match_id: int):
    db = get_db()
    col = db["matches"]
    m = await col.find_one({"id": match_id})
    if not m:
        return Response(
            content='{"error":"Partido no encontrado"}',
            status_code=404,
            media_type="application/json",
        )
    return strip_mongo_id(m)


@router.post("")
async def upsert_match(payload: MatchIn):
    db = get_db()
    col = db["matches"]

    local = null_if_empty(payload.local)
    visit = null_if_empty(payload.visit)

    if not local or not visit:
        return Response(
            content='{"error":"Equipo local y visitante son obligatorios"}',
            status_code=400,
            media_type="application/json",
        )

    fields: dict[str, Any] = {
        "fase": payload.fase or "Grupos",
        "jornada": int(payload.jornada) if null_if_empty(payload.jornada) is not None else None,
        "local": int(local),
        "visit": int(visit),
        "gL": None if payload.gL is None else int(payload.gL),
        "gV": None if payload.gV is None else int(payload.gV),
        "fecha": null_if_empty(payload.fecha),
        "hora": null_if_empty(payload.hora),
        "cancha": payload.cancha or "Estadio Municipal",
        "estado": payload.estado or "Programado",
        "mvp": int(payload.mvp) if null_if_empty(payload.mvp) is not None else None,
        "eventos": [e.model_dump() for e in payload.eventos] if payload.eventos else [],
    }

    if payload.id:
        match_id = payload.id
        await col.update_one({"id": match_id}, {"$set": fields})
    else:
        match_id = await next_id(col)
        await col.insert_one({"id": match_id, **fields})

    await recalc_standings(db)

    saved = await col.find_one({"id": match_id})
    return strip_mongo_id(saved)


@router.delete("")
async def delete_match(id: Optional[int] = None):
    db = get_db()
    col = db["matches"]
    if id:
        await col.delete_one({"id": id})
        await recalc_standings(db)
    return {"deleted": True}
