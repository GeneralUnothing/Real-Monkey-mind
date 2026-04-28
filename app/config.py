# app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "studymind")
    
    # AI APIs
    FEATHERLESS_API_KEY: str = os.getenv("FEATHERLESS_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-super-secret-key-change-this")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
    
    # CORS
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    
    # ML
    ML_MODELS_DIR: str = os.getenv("ML_MODELS_DIR", "ml_models")

settings = Settings()
