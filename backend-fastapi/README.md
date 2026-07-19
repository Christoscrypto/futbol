# DIMA CUP — Backend en FastAPI

Migración del backend de **Node/Netlify Functions** a **FastAPI (Python)**,
usando la **misma base de datos de MongoDB Atlas** que ya tenías (no se
pierde ningún dato, solo cambia el motor que la sirve).

## ⚠️ Importante: por qué es un proyecto aparte

Netlify Functions solo ejecuta JavaScript/Node. FastAPI es Python, así
que **no puede vivir dentro de Netlify**. Por eso este backend se
despliega en un servicio aparte (Render, Railway o Fly.io — los tres
tienen plan gratis) y el frontend (que se sigue publicando en Netlify)
le pega por internet, igual que antes le pegaba a `/api/*`.

```
Netlify (frontend, HTML/CSS/JS estático)
   │
   │  fetch('https://tu-backend.onrender.com/api/teams', ...)
   ▼
Render/Railway/Fly (backend FastAPI)
   │
   ▼
MongoDB Atlas (misma base de siempre)
```

## Estructura

```
backend-fastapi/
├── app/
│   ├── main.py              # arranca FastAPI, monta routers, CORS
│   ├── db.py                # conexión a Mongo (equivalente a _db.js)
│   └── routers/
│       ├── teams.py         # GET/POST/DELETE /api/teams
│       ├── players.py       # GET/POST/DELETE /api/players
│       ├── matches.py       # GET/POST/DELETE /api/matches (+ recalculo de tabla)
│       ├── news.py          # GET/POST/DELETE /api/news
│       └── sponsors.py      # GET/POST/DELETE /api/sponsors
├── requirements.txt
├── .env.example
├── Procfile                 # para Render/Railway
└── render.yaml              # despliegue con un clic en Render
```

Cada router es una traducción 1:1 de su función de Netlify equivalente:
mismos nombres de colección, mismos campos, mismo cálculo de
`recalcStandings`, mismo orden de patrocinadores por tier, etc.

## 1. Correrlo en tu computadora

```bash
cd backend-fastapi
python3 -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edita .env y pon tu MONGODB_URI real (la misma que ya usabas)

uvicorn app.main:app --reload --port 8000
```

Pruébalo abriendo `http://localhost:8000/api/teams` — deberías ver tus
equipos ya existentes en MongoDB Atlas (no hace falta volver a hacer
seed, la base es la misma).

Documentación interactiva automática: `http://localhost:8000/docs`

## 2. Desplegarlo (recomendado: Render, gratis)

1. Sube esta carpeta `backend-fastapi/` a un repo de GitHub (puede ser
   el mismo repo del frontend, en una subcarpeta, o uno aparte).
2. En [render.com](https://render.com) → **New → Web Service** →
   conecta tu repo.
3. Render detecta `render.yaml` automáticamente. Si no, configura a mano:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. En **Environment**, agrega:
   - `MONGODB_URI` → tu cadena de conexión real de Atlas
   - `MONGODB_DB` → `dimacup`
   - `ALLOWED_ORIGINS` → la URL de tu sitio en Netlify (o `*` mientras pruebas)
5. Deploy. Render te da una URL tipo `https://dimacup-api.onrender.com`.

**Alternativas igual de válidas:** Railway.app y Fly.io funcionan
prácticamente igual (mismo `Procfile`, mismas env vars).

> Nota sobre el plan gratis de Render: el servicio "duerme" tras 15 min
> sin tráfico y tarda ~30-50s en despertar en la siguiente petición. Si
> eso te molesta para producción, considera el plan pagado más barato
> o Railway (arranque más rápido en frío).

## 3. Conectar el frontend

En `frontend/js/shared.js`, ya dejé esta línea lista para que edites:

```js
const API_BASE = 'https://TU-BACKEND-FASTAPI.onrender.com/api';
```

Cámbiala por la URL real que te dio Render (o el servicio que uses), y
vuelve a publicar el frontend en Netlify. Eso es todo — no necesitas
tocar ninguna otra página, todas usan `Api.get/post/del` desde
`shared.js`.

## 4. CORS

`ALLOWED_ORIGINS` en el `.env` del backend controla qué dominios pueden
llamar a la API desde el navegador. Mientras pruebas puedes dejarlo en
`*`; para producción, ponlo como tu dominio real de Netlify, por ejemplo:

```
ALLOWED_ORIGINS=https://dimacup.netlify.app
```

(Puedes poner varios separados por coma.)

## Endpoints

Todos idénticos a los que ya tenía tu frontend, solo que ahora los sirve
FastAPI en vez de Netlify Functions:

| Método | Ruta            | Notas                                              |
|--------|-----------------|-----------------------------------------------------|
| GET    | `/api/teams`    | lista equipos                                       |
| POST   | `/api/teams`    | crea o actualiza (manda `id` para actualizar)       |
| DELETE | `/api/teams?id=1` | borra equipo + limpia jugadores/partidos relacionados |
| GET/POST/DELETE | `/api/players`  | igual, con mapeo `team_id` ⇄ `team`         |
| GET/POST/DELETE | `/api/matches`  | POST y DELETE recalculan automáticamente la tabla de posiciones |
| GET/POST/DELETE | `/api/news`     | —                                             |
| GET/POST/DELETE | `/api/sponsors` | ordenados por tier (Platino→Bronce)           |
