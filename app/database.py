# app/database.py - NO MongoDB REQUIRED VERSION
import os
from dotenv import load_dotenv

load_dotenv()

# Try to import motor, but don't fail if not installed
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MOTOR_AVAILABLE = True
except ImportError:
    MOTOR_AVAILABLE = False
    print("Motor not installed - running in demo mode without database")

_client = None
_database = None

async def connect_db():
    """Connect to MongoDB (or use mock if not available)"""
    global _client, _database
    
    if not MOTOR_AVAILABLE:
        print("Running in DEMO MODE - no database connection")
        return None
    
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "monkeymind")
    
    try:
        # Timeout quickly (2 seconds) if MongoDB isn't running
        _client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
        # Test connection
        await _client.admin.command('ping')
        _database = _client[DATABASE_NAME]
        print("SUCCESS: Database Connected: Using MongoDB")
        return _database
    except Exception:
        # Silent fallback to Demo Mode
        print("INFO: Running in Demo Mode (No database connected)")
        _database = None
        return None

async def close_db():
    """Close MongoDB connection"""
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed")

def get_db():
    """Get database instance (may be None in demo mode)"""
    return _database

def get_collection(collection_name: str):
    """Get collection (returns mock if no database)"""
    if _database is None:
        # Return a mock collection for demo
        return None
    return _database[collection_name]
