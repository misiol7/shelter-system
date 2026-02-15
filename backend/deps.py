from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import SessionLocal
from auth import decode_token
from models import User

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def current_admin(cred:HTTPAuthorizationCredentials=Depends(security), db:Session=Depends(get_db)):
    try:
        uid = int(decode_token(cred.credentials)["sub"])
    except Exception:
        raise HTTPException(401,"Invalid token")
    user = db.query(User).get(uid)
    if not user or user.role!="admin":
        raise HTTPException(403,"Admin only")
    return user
