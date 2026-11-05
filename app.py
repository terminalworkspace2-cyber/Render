import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Req(BaseModel):
    prompt: str

@app.get("/")
def root():
    return {"status": "ok", "mode": "no-token"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate(r: Req):
    # Free, no token needed
    url = f"https://text.pollinations.ai/{r.prompt}"
    resp = requests.get(url, timeout=60)
    return {"result": resp.text}

@app.post("/v1/chat/completions")
def chat(payload: dict):
    msgs = payload.get("messages", [])
    prompt = "\n".join([m.get("content","") for m in msgs])
    return generate(Req(prompt=prompt))
