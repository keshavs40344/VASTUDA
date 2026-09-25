import time
import threading
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RateLimiter", version="1.0.0")

class ConsumeReq(BaseModel):
    client_id: str = "default"
    tokens: int = 1

tokens = 10.0
lock = threading.Lock()

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/consume")
def consume(req: ConsumeReq):
    global tokens
    with lock:
        if tokens >= req.tokens:
            tokens -= req.tokens
            return {"allowed": True, "remaining": tokens}
        return {"allowed": False, "remaining": tokens}