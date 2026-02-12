"""
JWT Authentication for Incident Responder API

JWT (JSON Web Token) is a secure way to authenticate API requests.
How it works:
1. User logs in with username/password → Get JWT token
2. User includes token in API requests → Verify token
3. Token expires after X hours → User must login again
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
import bcrypt
import os

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token expires in 1 hour

# Security scheme
security = HTTPBearer()


# Models
class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = False


class UserInDB(User):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# Fake user database (in production, use real database)
fake_users_db = {
    "admin": {
        "username": "admin",
        "email": "admin@company.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
    },
    "john": {
        "username": "john",
        "email": "john@company.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
    }
}


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password using bcrypt.
    """
    try:
        # Convert to bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


# User utilities
def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in token (usually {"sub": username})
        expires_delta: How long until token expires
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Encode the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData with username, or None if invalid
    """
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
        
        return TokenData(username=username)
    
    except JWTError:
        return None


# Dependency for protected routes
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Dependency to get current user from JWT token.
    Supports both formats:
    - Authorization: Bearer <token>  (Standard OAuth 2.0)
    - Authorization: <token>         (AWS Cognito style)
    
    Args:
        credentials: HTTP Authorization header with Bearer token
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from Authorization header
    token = credentials.credentials
    
    # Handle AWS Cognito style (token might have "Bearer " prefix or not)
    # If someone sends "Authorization: Bearer Bearer <token>", clean it up
    if token.startswith("Bearer "):
        token = token[7:]  # Remove "Bearer " prefix
    
    # Decode token
    token_data = decode_access_token(token)
    if token_data is None or token_data.username is None:
        raise credentials_exception
    
    # Get user from database
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Check if user is disabled
    if user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current active user.
    This is a convenience wrapper around get_current_user.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Helper function to create a new user (for testing)
def create_user(username: str, password: str, email: str) -> dict:
    """
    Create a new user (for testing purposes).
    In production, this would be an API endpoint with proper validation.
    """
    hashed_password = get_password_hash(password)
    
    user = {
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "disabled": False
    }
    
    fake_users_db[username] = user
    
    return {
        "username": username,
        "email": email,
        "message": "User created successfully"
    }


if __name__ == "__main__":
    # Test: Create a new user
    print("Creating test user...")
    result = create_user("testuser", "testpass123", "test@company.com")
    print(result)
    
    # Test: Authenticate user
    print("\nAuthenticating user...")
    user = authenticate_user("testuser", "testpass123")
    if user:
        print(f"✅ Authentication successful: {user.username}")
    else:
        print("❌ Authentication failed")
    
    # Test: Create JWT token
    print("\nCreating JWT token...")
    token = create_access_token(data={"sub": user.username})
    print(f"Token: {token[:50]}...")
    
    # Test: Decode JWT token
    print("\nDecoding JWT token...")
    token_data = decode_access_token(token)
    if token_data:
        print(f"✅ Token valid: username={token_data.username}")
    else:
        print("❌ Token invalid")
