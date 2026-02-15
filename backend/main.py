
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from datetime import datetime, timedelta
import json, csv, io
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DATABASE_URL = "postgresql://postgres:postgres@postgres:5432/shelter"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Dog(Base):
    __tablename__ = "dogs"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    available = Column(Boolean, default=True)
    status = Column(String, default="IN_KENNEL")
    walks = relationship("Walk", back_populates="dog", cascade="all,delete")

class Walk(Base):
    __tablename__ = "walks"
    id = Column(Integer, primary_key=True)
    dog_id = Column(Integer, ForeignKey("dogs.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    dog = relationship("Dog", back_populates="walks")

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ================= WEBSOCKET =================

class WSManager:
    def __init__(self):
        self.clients = []

    async def connect(self, ws):
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self):
        dead = []
        for c in self.clients:
            try:
                await c.send_text("update")
            except:
                dead.append(c)
        for d in dead:
            self.disconnect(d)

ws = WSManager()

@app.websocket("/ws")
async def ws_endpoint(socket: WebSocket):
    await ws.connect(socket)
    try:
        while True:
            await socket.receive_text()
    except WebSocketDisconnect:
        ws.disconnect(socket)

# ================= API =================

def daily_minutes(db, dog_id):
    today = datetime.utcnow().date()
    start = datetime(today.year,today.month,today.day)
    end = start + timedelta(days=1)
    walks = db.query(Walk).filter(
        Walk.dog_id==dog_id,
        Walk.start_time>=start,
        Walk.start_time<end
    ).all()
    total = 0
    for w in walks:
        stop = w.end_time or datetime.utcnow()
        total += int((stop-w.start_time).total_seconds()/60)
    return total

@app.get("/dogs")
def dogs(db: Session = Depends(get_db)):
    out=[]
    for d in db.query(Dog).all():
        active = db.query(Walk).filter(Walk.dog_id==d.id, Walk.end_time==None).first()
        out.append({
            "id": d.id,
            "name": d.name,
            "available": d.available,
            "status": d.status,
            "daily_minutes": daily_minutes(db,d.id),
            "walk_started": active.start_time.isoformat() if active else None
        })
    return out

@app.post("/walk/start")
async def start_walk(dog_id:int, db:Session=Depends(get_db)):
    dog=db.get(Dog,dog_id)
    if not dog: raise HTTPException(404)
    dog.status="WALKING"
    db.add(Walk(dog_id=dog.id))
    db.commit()
    await ws.broadcast()
    return {"ok":True}

@app.post("/walk/stop")
async def stop_walk(dog_id:int, db:Session=Depends(get_db)):
    dog=db.get(Dog,dog_id)
    walk=db.query(Walk).filter(Walk.dog_id==dog_id, Walk.end_time==None).first()
    if not walk: raise HTTPException(404)
    walk.end_time=datetime.utcnow()
    dog.status="IN_KENNEL"
    db.commit()
    await ws.broadcast()
    return {"ok":True}

@app.post("/admin/dogs")
async def add_dog(name:str, db:Session=Depends(get_db)):
    db.add(Dog(name=name))
    db.commit()
    await ws.broadcast()
    return {"ok":True}

@app.delete("/admin/dogs/{dog_id}")
async def delete_dog(dog_id:int, db:Session=Depends(get_db)):
    d=db.get(Dog,dog_id)
    if not d: raise HTTPException(404)
    db.delete(d)
    db.commit()
    await ws.broadcast()
    return {"ok":True}

# ================= EXPORT PDF =================

@app.get("/admin/export/today/pdf")
def export_pdf(db:Session=Depends(get_db)):
    today=datetime.utcnow().date()
    start=datetime(today.year,today.month,today.day)
    end=start+timedelta(days=1)
    walks=db.query(Walk).filter(Walk.start_time>=start, Walk.start_time<end).all()

    buffer=io.BytesIO()
    pdf=canvas.Canvas(buffer,pagesize=A4)
    y=800
    pdf.drawString(50,y,"Raport spacerow - schronisko")
    y-=30

    for w in walks:
        stop=w.end_time or datetime.utcnow()
        mins=int((stop-w.start_time).total_seconds()/60)
        pdf.drawString(50,y,f"{w.dog.name} | {mins} min")
        y-=15
        if y<80:
            pdf.showPage()
            y=800

    pdf.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition":"attachment; filename=raport.pdf"})
