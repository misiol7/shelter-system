from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

SECRET = "CHANGE_ME_SUPER_SECRET"
ALGO = "HS256"
pwd = CryptContext(schemes=["bcrypt"])

def hash_password(p): return pwd.hash(p)
def verify_password(p,h): return pwd.verify(p,h)

def create_token(uid):
    return jwt.encode({"sub":str(uid),"exp":datetime.utcnow()+timedelta(hours=12)}, SECRET, algorithm=ALGO)

def decode_token(token):
    return jwt.decode(token, SECRET, algorithms=[ALGO])
