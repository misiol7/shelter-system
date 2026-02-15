
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, date
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from jose import jwt
from passlib.context import CryptContext
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DATABASE_URL = os.getenv("DATABASE_URL","postgresql+psycopg2://postgres:postgres@postgres:5432/shelter")
SECRET_KEY = os.getenv("SECRET_KEY","change_me")
ALGO = "HS256"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class User(Base):
    __tablename__="users"
    id=Column(Integer, primary_key=True)
    username=Column(String, unique=True, nullable=False)
    password_hash=Column(String, nullable=False)
    role=Column(String, default="volunteer")

class Dog(Base):
    __tablename__="dogs"
    id=Column(Integer, primary_key=True)
    name=Column(String, unique=True, nullable=False)
    available=Column(Boolean, default=True)
    active_walk_id=Column(Integer, nullable=True)
    notes=Column(Text, default="")

class Walk(Base):
    __tablename__="walks"
    id=Column(Integer, primary_key=True)
    dog_id=Column(Integer, ForeignKey("dogs.id"))
    user_id=Column(Integer, ForeignKey("users.id"))
    start_time=Column(DateTime, default=datetime.utcnow)
    end_time=Column(DateTime, nullable=True)
    notes=Column(Text, default="")
    dog=relationship("Dog")
    user=relationship("User")

Base.metadata.create_all(engine)

def seed():
    db=SessionLocal()
    if not db.query(User).first():
        db.add(User(username="admin", password_hash=pwd.hash("admin123"), role="admin"))
        db.add(User(username="wolontariusz", password_hash=pwd.hash("wolontariusz123"), role="volunteer"))
        db.add_all([Dog(name="Burek"), Dog(name="Luna"), Dog(name="Azor")])
        db.commit()
    db.close()
seed()

app=FastAPI(title="Schronisko PRO MAX REAL v3")

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

def token_for(u):
    return jwt.encode({"sub":u.username,"role":u.role}, SECRET_KEY, algorithm=ALGO)

def current_user(c:HTTPAuthorizationCredentials=Depends(security), db:Session=Depends(get_db)):
    try:
        payload=jwt.decode(c.credentials, SECRET_KEY, algorithms=[ALGO])
        u=db.query(User).filter_by(username=payload["sub"]).first()
        if not u:
            raise Exception()
        return u
    except Exception:
        raise HTTPException(401,"Invalid token")

def require_admin(u=Depends(current_user)):
    if u.role!="admin":
        raise HTTPException(403,"Admin only")
    return u

class LoginIn(BaseModel):
    username:str
    password:str

class DogIn(BaseModel):
    name:str
    available:bool=True
    notes:str=""

class WalkStart(BaseModel):
    dog_id:int
    notes:str=""

class WalkEnd(BaseModel):
    walk_id:int
    notes:str=""

class WSManager:
    def __init__(self):
        self.clients=[]
    async def connect(self, ws:WebSocket):
        await ws.accept()
        self.clients.append(ws)
    def disconnect(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)
    async def broadcast(self, msg):
        dead=[]
        for c in self.clients:
            try:
                await c.send_json(msg)
            except Exception:
                dead.append(c)
        for d in dead:
            self.disconnect(d)

wsman=WSManager()

@app.get("/api/health")
def health():
    return {"ok":True}

@app.post("/api/login")
def login(data:LoginIn, db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=data.username).first()
    if not u or not pwd.verify(data.password, u.password_hash):
        raise HTTPException(401,"Bad credentials")
    return {"token":token_for(u),"role":u.role}

@app.get("/api/dogs")
def list_dogs(db:Session=Depends(get_db)):
    out=[]
    for d in db.query(Dog).all():
        out.append({"id":d.id,"name":d.name,"available":d.available,"status":"walking" if d.active_walk_id else "cage"})
    return out

@app.post("/api/dogs")
async def add_dog(data:DogIn, db:Session=Depends(get_db), _=Depends(require_admin)):
    d=Dog(name=data.name, available=data.available, notes=data.notes)
    db.add(d); db.commit()
    await wsman.broadcast({"type":"REFRESH"})
    return {"ok":True}

@app.delete("/api/dogs/{dog_id}")
async def delete_dog(dog_id:int, db:Session=Depends(get_db), _=Depends(require_admin)):
    d=db.get(Dog,dog_id)
    if d:
        db.delete(d)
        db.commit()
    await wsman.broadcast({"type":"REFRESH"})
    return {"ok":True}

@app.post("/api/walk/start")
async def walk_start(data:WalkStart, db:Session=Depends(get_db), u=Depends(current_user)):
    dog=db.get(Dog,data.dog_id)
    if not dog or dog.active_walk_id:
        raise HTTPException(400,"Dog unavailable")
    w=Walk(dog_id=dog.id,user_id=u.id,start_time=datetime.utcnow(),notes=data.notes)
    db.add(w); db.commit(); db.refresh(w)
    dog.active_walk_id=w.id
    db.commit()
    await wsman.broadcast({"type":"REFRESH"})
    return {"walk_id":w.id}

@app.post("/api/walk/end")
async def walk_end(data:WalkEnd, db:Session=Depends(get_db), _=Depends(current_user)):
    w=db.get(Walk,data.walk_id)
    if not w or w.end_time:
        raise HTTPException(400,"Invalid")
    w.end_time=datetime.utcnow()
    dog=db.get(Dog,w.dog_id)
    if dog:
        dog.active_walk_id=None
    db.commit()
    await wsman.broadcast({"type":"REFRESH"})
    return {"ok":True}

def today_df(db):
    start=datetime.combine(date.today(), datetime.min.time())
    walks=db.query(Walk).filter(Walk.start_time>=start).all()
    rows=[]
    for w in walks:
        end=w.end_time or datetime.utcnow()
        rows.append({
            "dog": w.dog.name if w.dog else "",
            "volunteer": w.user.username if w.user else "",
            "start": w.start_time.isoformat(sep=" ",timespec="minutes"),
            "end": end.isoformat(sep=" ",timespec="minutes"),
            "minutes": int((end-w.start_time).total_seconds()/60),
            "notes": w.notes or ""
        })
    return pd.DataFrame(rows)

@app.get("/api/export/daily.csv")
def export_csv(db:Session=Depends(get_db)):
    df=today_df(db)
    path="/tmp/daily.csv"
    df.to_csv(path,index=False)
    return FileResponse(path, filename="daily_walks.csv")

@app.get("/api/export/daily.xlsx")
def export_xlsx(db:Session=Depends(get_db)):
    df=today_df(db)
    path="/tmp/daily.xlsx"
    df.to_excel(path,index=False)
    return FileResponse(path, filename="daily_walks.xlsx")

@app.get("/api/export/daily.pdf")
def export_pdf(db:Session=Depends(get_db)):
    df=today_df(db)
    path="/tmp/daily.pdf"
    c=canvas.Canvas(path,pagesize=A4)
    y=800
    c.drawString(40,y,"Schronisko PRO MAX REAL v3 - Raport dzienny")
    y-=25
    for _,r in df.head(35).iterrows():
        c.drawString(40,y,f"{r['dog']} | {r['volunteer']} | {r['minutes']} min")
        y-=16
        if y<60:
            c.showPage()
            y=800
    c.save()
    return FileResponse(path, filename="daily_walks.pdf")

@app.websocket("/ws")
async def websocket_endpoint(ws:WebSocket):
    await wsman.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        wsman.disconnect(ws)
