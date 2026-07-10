from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, ensure_project_root_on_path

ensure_project_root_on_path()

from app.migrations import init_database
from app.routers import auth, chat, export, generate, sessions

app = FastAPI(title="AI Study Assistant API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(generate.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(export.router)


@app.on_event("startup")
def on_startup():
    init_database()


@app.get("/api/health")
def health():
    return {"status": "ok"}
