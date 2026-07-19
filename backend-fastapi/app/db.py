"""
DIMA CUP — Conexión a MongoDB compartida entre routers
=======================================================
Equivalente en FastAPI de netlify/functions/_db.js.
Usa motor (driver async oficial de MongoDB para asyncio) y mantiene
un único cliente para toda la vida de la app (igual que el "cached
client" que se usaba en las Netlify Functions).
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    """Devuelve la base de datos ya conectada. Se llama desde cada request."""
    global _client, _db
    if _db is not None:
        return _db

    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "Falta la variable de entorno MONGODB_URI. Configúrala en tu "
            "archivo .env (local) o en el panel de tu hosting (producción)."
        )

    _client = AsyncIOMotorClient(uri)
    _db = _client[os.getenv("MONGODB_DB", "dimacup")]
    return _db


async def next_id(collection) -> int:
    """Calcula el siguiente id numérico autoincremental de una colección."""
    last = await collection.find().sort("id", -1).limit(1).to_list(length=1)
    return (last[0]["id"] + 1) if last else 1


def null_if_empty(val):
    """Convierte '' o None en None (equivalente a nullIfEmpty en el JS original)."""
    if val is None or val == "":
        return None
    return val


def strip_mongo_id(doc: dict | None) -> dict | None:
    """Quita el campo _id de Mongo antes de mandar el documento al frontend."""
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("_id", None)
    return doc
