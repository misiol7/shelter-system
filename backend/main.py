from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from database import Base, engine
from models import User, Dog, Walk
from deps import get_db, current_admin
from auth import verify_password, create_token

app = FastAPI()
Base.metadata.create_all(bind=engine)

class WSManager:
    def __init__(self):
        self.clients = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, data):
        for c in list(self.clients):
            try:
                await c.send_text(json.dumps(data))
            except Exception:
                pass

ws_manager = WSManager()

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

def daily_minutes(db: Session, dog_id: int):
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    end = start + timedelta(days=1)
    rows = db.query(Walk).filter(
        Walk.dog_id == dog_id,
        Walk.start_time >= start,
        Walk.start_time < end
    ).all()
    total = 0
    for w in rows:
        stop = w.end_time or datetime.utcnow()
        total += int((stop - w.start_time).total_seconds() // 60)
    return total

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/dogs")
def dogs(db: Session = Depends(get_db)):
    out = []
    for d in db.query(Dog).all():
        out.append({
            "id": d.id,
            "name": d.name,
            "available": d.available,
            "status": d.status,
            "daily_minutes": daily_minutes(db, d.id)
        })
    return out

@app.post("/walk/start")
async def start_walk(dog_id: int, db: Session = Depends(get_db)):
    dog = db.query(Dog).get(dog_id)
    if not dog or not dog.available or dog.status != "IN_KENNEL":
        raise HTTPException(400, "Dog unavailable")

    dog.status = "WALKING"
    db.add(Walk(dog_id=dog.id, admin_id=1))
    db.commit()
    await ws_manager.broadcast({"type":"DOG_UPDATE"})
    return {"ok": True}

@app.post("/walk/stop")
async def stop_walk(dog_id: int, db: Session = Depends(get_db)):
    dog = db.query(Dog).get(dog_id)
    walk = db.query(Walk).filter(Walk.dog_id==dog_id, Walk.end_time==None).first()
    if not dog or not walk:
        raise HTTPException(404, "No active walk")

    walk.end_time = datetime.utcnow()
    dog.status = "IN_KENNEL"
    db.commit()
    await ws_manager.broadcast({"type":"DOG_UPDATE"})
    return {"ok": True}

@app.post("/admin/login")
def admin_login(username: str, password: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username==username).first()
    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(401, "Bad credentials")
    return {"token": create_token(u.id)}

@app.post("/admin/dogs")
def add_dog(name: str, admin=Depends(current_admin), db: Session = Depends(get_db)):
    db.add(Dog(name=name))
    db.commit()
    return {"ok": True}

@app.post("/admin/dogs/{dog_id}/availability")
def set_availability(dog_id:int, available: bool,
                     admin=Depends(current_admin),
                     db: Session = Depends(get_db)):
    d = db.query(Dog).get(dog_id)
    if not d:
        raise HTTPException(404, "Dog not found")
    d.available = available
    if not available:
        d.status = "UNAVAILABLE"
    elif d.status == "UNAVAILABLE":
        d.status = "IN_KENNEL"
    db.commit()
    return {"ok": True}
