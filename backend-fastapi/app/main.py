"""
DIMA CUP — Backend en FastAPI
=============================
Migración del backend Node/Netlify Functions a FastAPI + MongoDB Atlas
(misma base de datos, mismos endpoints, mismo comportamiento).

Endpoints (idénticos a los que ya usa js/shared.js vía /api/*):
  GET/POST/DELETE  /api/teams
  GET/POST/DELETE  /api/players
  GET/POST/DELETE  /api/matches
  GET/POST/DELETE  /api/news
  GET/POST/DELETE  /api/sponsors
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .routers import teams, players, matches, news, sponsors  # noqa: E402

app = FastAPI(title="DIMA CUP API")

# CORS: mismos headers que tenía _db.js (Access-Control-Allow-Origin: *).
# Si quieres restringirlo a tu dominio real, cambia allow_origins.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins.split(",")] if allowed_origins != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(news.router)
app.include_router(sponsors.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
