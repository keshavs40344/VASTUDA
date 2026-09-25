import time
import threading
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RateLimiter", version="2.0.0")

class ConsumeReq(BaseModel):
    client_id: str = "default"
    tokens: int = 1

class ConfigReq(BaseModel):
    max_capacity: float

tokens = 50.0
capacity = 50.0
lock = threading.Lock()

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}

@app.post("/consume")
def consume(req: ConsumeReq):
    global tokens
    with lock:
        if tokens >= req.tokens:
            tokens -= req.tokens
            return {"allowed": True, "remaining": tokens}
        return {"allowed": False, "remaining": tokens}

@app.post("/config")
def set_config(cfg: ConfigReq):
    global capacity
    capacity = cfg.max_capacity
    return {"status": "updated", "capacity": capacity}