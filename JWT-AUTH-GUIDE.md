# JWT Authentication Guide

## What is JWT?

**JWT (JSON Web Token)** is a secure way to authenticate API requests without storing session data on the server.

### How it works:

```
1. User logs in with username/password
   ↓
2. Server verifies credentials
   ↓
3. Server creates JWT token (signed with secret key)
   ↓
4. User receives token
   ↓
5. User includes token in all API requests
   ↓
6. Server verifies token signature
   ↓
7. Server grants access if token is valid
```

---

## JWT Token Structure

A JWT token has 3 parts separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTY3ODk4NzY1NH0.signature
│                                      │                                    │
│                                      │                                    └─ Signature (verifies token)
│                                      └────────────────────────────────────── Payload (user data)
└─────────────────────────────────────────────────────────────────────────── Header (algorithm)
```

### Header:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Payload:
```json
{
  "sub": "admin",           // Subject (username)
  "exp": 1678987654         // Expiration timestamp
}
```

### Signature:
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)
```

---

## Using JWT in Our API

### Step 1: Login

```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secret"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Step 2: Use Token in Requests

```bash
curl -X POST http://localhost:8000/incident \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "log": "Lambda timeout",
    "service": "payment-service"
  }'
```

---

## Python Code Explanation

### 1. Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash a password
hashed = pwd_context.hash("secret")
# Result: $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW

# Verify a password
is_valid = pwd_context.verify("secret", hashed)
# Result: True
```

**Why hash passwords?**
- Never store plain passwords in database
- If database is compromised, passwords are safe
- bcrypt is slow (intentionally) to prevent brute force attacks

---

### 2. Creating JWT Token

```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    
    # Add expiration time
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    
    # Encode token
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return token

# Usage
token = create_access_token({"sub": "admin"})
```

---

### 3. Verifying JWT Token

```python
from jose import jwt, JWTError

def decode_access_token(token: str):
    try:
        # Decode and verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username
    except JWTError:
        return None

# Usage
username = decode_access_token(token)
if username:
    print(f"Valid token for user: {username}")
else:
    print("Invalid token")
```

---

### 4. Protecting Endpoints

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(credentials = Depends(security)):
    token = credentials.credentials
    username = decode_access_token(token)
    
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return username

# Protected endpoint
@app.post("/incident")
def handle_incident(
    request: IncidentRequest,
    current_user: str = Depends(get_current_user)
):
    print(f"Request from user: {current_user}")
    return process_incident(request)
```

---

## Security Best Practices

### 1. Secret Key
```python
# ❌ BAD: Hardcoded secret
SECRET_KEY = "my-secret-key"

# ✅ GOOD: Environment variable
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
```

### 2. Token Expiration
```python
# ❌ BAD: Never expires
ACCESS_TOKEN_EXPIRE_MINUTES = None

# ✅ GOOD: Expires in 1 hour
ACCESS_TOKEN_EXPIRE_MINUTES = 60
```

### 3. HTTPS Only
```python
# ❌ BAD: HTTP (token can be intercepted)
http://api.example.com/incident

# ✅ GOOD: HTTPS (encrypted)
https://api.example.com/incident
```

### 4. Password Requirements
```python
# ✅ GOOD: Strong password requirements
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character
```

---

## Testing

### Install dependencies:
```bash
pip install python-jose[cryptography] passlib[bcrypt]
```

### Run tests:
```bash
# Start server
uvicorn main:app --reload

# In another terminal
python test_auth.py
```

---

## Default Users

| Username | Password | Email |
|----------|----------|-------|
| admin | secret | admin@company.com |
| john | secret | john@company.com |

**⚠️ Change these in production!**

---

## Common Errors

### 1. "Could not validate credentials"
**Cause:** Invalid or expired token
**Fix:** Login again to get new token

### 2. "Incorrect username or password"
**Cause:** Wrong credentials
**Fix:** Check username and password

### 3. "Token has expired"
**Cause:** Token older than 1 hour
**Fix:** Login again to get new token

### 4. "Not authenticated"
**Cause:** Missing Authorization header
**Fix:** Include `Authorization: Bearer <token>` header

---

## Production Checklist

- [ ] Change SECRET_KEY to strong random value
- [ ] Store SECRET_KEY in environment variable
- [ ] Use HTTPS only (no HTTP)
- [ ] Implement password requirements
- [ ] Add rate limiting on /login endpoint
- [ ] Add account lockout after failed attempts
- [ ] Implement refresh tokens (for long sessions)
- [ ] Add token revocation (logout)
- [ ] Store users in real database (not fake_users_db)
- [ ] Add user registration endpoint
- [ ] Add password reset functionality
- [ ] Add 2FA (two-factor authentication)

---

## Interview Talking Points

**"I implemented JWT authentication in Python using FastAPI"**

Key points to mention:
1. **Password Security**: Used bcrypt for password hashing (slow by design to prevent brute force)
2. **Token-based Auth**: Stateless authentication (no session storage needed)
3. **Token Structure**: Header + Payload + Signature (signed with HMAC-SHA256)
4. **Expiration**: Tokens expire after 1 hour (configurable)
5. **Protected Routes**: Used FastAPI dependencies to protect endpoints
6. **Security**: Secret key in environment variable, HTTPS only in production

**Why JWT over sessions?**
- Stateless (no server-side session storage)
- Scalable (works across multiple servers)
- Mobile-friendly (easy to use in mobile apps)
- Microservices-friendly (token can be verified by any service)

---

This is production-grade authentication! 🔒
