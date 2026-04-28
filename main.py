# main.py - FIXED VERSION for your structure
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys

# --- DIAGNOSTIC LOGGING (Visible on Render) ---
print("--- MONKEYMIND DEBUG START ---")
print(f"Current Working Directory: {os.getcwd()}")
print(f"System Path: {sys.path}")
try:
    print(f"Root Directory Contents: {os.listdir(os.getcwd())}")
    if os.path.exists("app"):
        print(f"App Directory Contents: {os.listdir('app')}")
except Exception as e:
    print(f"Debug Error: {e}")
print("--- MONKEYMIND DEBUG END ---")

# Ensure the current directory is at the front of the path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv()

# Import your actual route files
try:
    from app.routes import ai, flashcards, admin
    from app.routes.turbolearn import router as turbolearn_router
    from app.routes.social import router as social_router
except ImportError as e:
    print(f"CRITICAL: Failed to import routes from 'app.routes': {e}")
    print("Attempting fallback imports (no 'app.' prefix)...")
    try:
        from routes import ai, flashcards, admin
        from routes.turbolearn import router as turbolearn_router
        from routes.social import router as social_router
    except ImportError as e2:
        print(f"CRITICAL: Fallback imports also failed: {e2}")
        raise e

# Try to import database, but don't fail if not available
try:
    from app.database import connect_db, close_db
except ImportError:
    # Create dummy functions if database.py doesn't exist
    async def connect_db():
        print("⚠️ Running without database")
        return None
    async def close_db():
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown"""
    await connect_db()
    yield
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="MonkeyMind AI",
    description="AI-powered academic assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your routes
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(flashcards.router, prefix="/api/flashcards", tags=["Flashcards"])
app.include_router(turbolearn_router, prefix="/api/ml", tags=["Machine Learning"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(social_router, prefix="/api/social", tags=["Social"])

# Mount static files
import os
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Health check / Frontend
@app.get("/")
async def root():
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {
        "message": "🐒 MonkeyMind AI is running! (Frontend not found)",
        "status": "healthy",
        "endpoints": {
            "ai": "/api/ai/chat",
            "flashcards": "/api/flashcards",
            "ml": "/api/ml/study-pattern"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "MonkeyMind AI"}

@app.get("/admin")
async def admin_page():
    if os.path.exists("frontend/admin.html"):
        return FileResponse("frontend/admin.html")
    raise HTTPException(status_code=404, detail="Admin interface not found")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("MonkeyMind AI Server")
    print("="*50)
    print("Server: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("="*50 + "\n")
    # NOTE: For auto-reload during development, run this app using:
    #   uvicorn main:app --reload
    # Running with reload=True inside main.py is not supported.
    uvicorn.run(app, host="0.0.0.0", port=8000)