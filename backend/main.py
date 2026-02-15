from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import csv
import io

from openpyxl import Workbook

from database import Base, engine
from models import User, Dog, Walk
from deps import get_db, current_admin
from auth import verify_password, create_token

app = FastAPI()
Base.metadata.create_all(bind=engine)

# =========================
# WEBSOCKET
# =========================

class WSManager:
    def __init__(self):
        self.clients = []

    async def connect(self, ws):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, data):
        dead = []
        for c in self.clients:
            try:
                await c.send_text(json.dumps(data))
            except:
                dead.append(c)

        for c in dead:
            self.disconnect(c)

ws_manager = WSManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)

# =========================
# HELPERS
# =========================

def daily_minutes(db: Session, dog_id: int):
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    end = start + timedelta(days=1)

    walks = db.query(Walk).filter(
        Walk.dog_id == dog_id,
        Walk.start_time >= start,
        Walk.start_time < end
    ).all()

    total = 0
    for w in walks:
        stop = w.end_time or datetime.utcnow()
        total += int((stop - w.start_time).total_seconds() // 60)

    return total

# =========================
# HEALTH
# =========================

@app.get("/health")
def health():
    return {"ok": True}

# =========================
# DOGS
# =========================

@app.get("/dogs")
def get_dogs(db: Session = Depends(get_db)):

    out = []

    for d in db.query(Dog).all():

        active_walk = db.query(Walk).filter(
            Walk.dog_id == d.id,
            Walk.end_time == None
        ).first()

        out.append({
            "id": d.id,
            "name": d.name,
            "available": d.available,
            "status": d.status,
            "daily_minutes": daily_minutes(db, d.id),
            "walk_started": active_walk.start_time.isoformat() if active_walk else None
        })

    return out

# =========================
# WALK
# =========================

@app.post("/walk/start")
async def start_walk(dog_id: int, db: Session = Depends(get_db)):

    dog = db.query(Dog).get(dog_id)

    if not dog or not dog.available or dog.status != "IN_KENNEL":
        raise HTTPException(400)

    dog.status = "WALKING"

    db.add(Walk(dog_id=dog.id, admin_id=1))
    db.commit()

    await ws_manager.broadcast({"type":"DOG_UPDATE"})
    return {"ok": True}

@app.post("/walk/stop")
async def stop_walk(dog_id: int, db: Session = Depends(get_db)):

    dog = db.query(Dog).get(dog_id)

    walk = db.query(Walk).filter(
        Walk.dog_id == dog_id,
        Walk.end_time == None
    ).first()

    if not dog or not walk:
        raise HTTPException(404)

    walk.end_time = datetime.utcnow()
    dog.status = "IN_KENNEL"
    db.commit()

    await ws_manager.broadcast({"type":"DOG_UPDATE"})
    return {"ok": True}

# =========================
# ADMIN
# =========================

@app.post("/admin/login")
def admin_login(username: str, password: str,
                db: Session = Depends(get_db)):

    u = db.query(User).filter(User.username == username).first()

    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(401)

    return {"token": create_token(u.id)}

@app.post("/admin/dogs")
async def add_dog(name:str,
                  admin=Depends(current_admin),
                  db:Session=Depends(get_db)):

    db.add(Dog(name=name))
    db.commit()

    await ws_manager.broadcast({"type":"DOG_UPDATE"})
    return {"ok":True}

@app.delete("/admin/dogs/{dog_id}")
async def delete_dog(dog_id:int,
                     admin=Depends(current_admin),
                     db:Session=Depends(get_db)):

    dog = db.query(Dog).get(dog_id)
    if not dog:
        raise HTTPException(404)

    db.query(Walk).filter(Walk.dog_id==dog_id).delete()
    db.delete(dog)
    db.commit()

    await ws_manager.broadcast({"type":"DOG_UPDATE"})
    return {"ok":True}

# =========================
# EXPORT CSV
# =========================

@app.get("/admin/export/today")
def export_today(admin=Depends(current_admin),
                 db: Session = Depends(get_db)):

    today = datetime.utcnow().date()
    start = datetime(today.year,today.month,today.day)
    end = start + timedelta(days=1)

    walks = db.query(Walk).filter(
        Walk.start_time >= start,
        Walk.start_time < end
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Dog","Start","Stop","Minutes"])

    for w in walks:
        stop = w.end_time or datetime.utcnow()
        mins = int((stop-w.start_time).total_seconds()/60)

        writer.writerow([
            w.dog.name if w.dog else "",
            w.start_time,
            w.end_time,
            mins
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition":"attachment; filename=spacery_dzis.csv"}
    )

# =========================
# EXPORT EXCEL
# =========================

@app.get("/admin/export/today/xlsx")
def export_today_xlsx(admin=Depends(current_admin),
                      db: Session = Depends(get_db)):

    today = datetime.utcnow().date()
    start = datetime(today.year,today.month,today.day)
    end = start + timedelta(days=1)

    walks = db.query(Walk).filter(
        Walk.start_time >= start,
        Walk.start_time < end
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Spacery"

    ws.append(["Dog","Start","Stop","Minutes"])

    for w in walks:
        stop = w.end_time or datetime.utcnow()
        mins = int((stop-w.start_time).total_seconds()/60)

        ws.append([
            w.dog.name if w.dog else "",
            str(w.start_time),
            str(w.end_time),
            mins
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition":"attachment; filename=spacery_dzis.xlsx"}
    )
