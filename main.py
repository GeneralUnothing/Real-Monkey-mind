# main.py
from contextlib import asynccontextmanager
import os
import sys
import uvicorn

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

# Import routes (app is installed as a package via pyproject.toml)
from app.routes import ai, flashcards, admin
from app.routes.turbolearn import router as turbolearn_router
from app.routes.social import router as social_router
from app.database import connect_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="MonkeyMind AI",
    description="AI-powered academic assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router,            prefix="/api/ai",       tags=["AI"])
app.include_router(flashcards.router,    prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(turbolearn_router,    prefix="/api/ml",       tags=["Machine Learning"])
app.include_router(admin.router,         prefix="/api/admin",    tags=["Admin"])
app.include_router(social_router,        prefix="/api/social",   tags=["Social"])

if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def root():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "MonkeyMind AI is running!", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "MonkeyMind AI"}


@app.get("/admin")
async def admin_page():
    if os.path.exists("frontend/admin.html"):
        return FileResponse("frontend/admin.html")
    raise HTTPException(status_code=404, detail="Admin interface not found")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("MonkeyMind AI Server")
    print("="*50)
    print("Server: http://localhost:8000")
    print("Docs:   http://localhost:8000/docs")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)