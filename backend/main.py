from fastapi import FastAPI
app=FastAPI()
@app.get('/health')
def h(): return {'ok':True}
@app.get('/dogs')
def d(): return []
