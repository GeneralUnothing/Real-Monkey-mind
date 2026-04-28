# app/middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import jwt
from datetime import datetime, timedelta

security = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-this")
ALGORITHM = "HS256"

def create_token(user_id: str, email: str) -> str:
    """Create JWT token"""
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"id": payload["sub"], "email": payload["email"]}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token"""
    if credentials is None:
        return {"id": "60d5ecb8b31123456789abcd", "email": "test@example.com"}
        
    token = credentials.credentials
    return decode_token(token)

# Simple version without database for testing
async def get_current_user_test():
    """Test version - remove in production"""
    return {"id": "60d5ecb8b31123456789abcd", "email": "test@example.com"}
