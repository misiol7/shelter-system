from database import SessionLocal
from models import User, Dog
from auth import hash_password

db = SessionLocal()

if not db.query(User).filter(User.username=="admin").first():
    db.add(User(
        username="admin",
        password_hash=hash_password("admin123"),
        role="admin"
    ))

for n in ["Burek","Luna","Reksio","Azor"]:
    if not db.query(Dog).filter(Dog.name==n).first():
        db.add(Dog(name=n))

db.commit()
db.close()
print("init done")
