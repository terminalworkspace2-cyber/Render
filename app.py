import os, requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

HF_TOKEN = os.environ.get("HF_TOKEN", "")
MODEL = os.environ.get("MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")

class Req(BaseModel):
    prompt: str
    max_tokens: int = 256

@app.get("/")
def root():
    return {"status": "ok", "model": MODEL, "mode": "hf-api"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate(r: Req):
    if not HF_TOKEN:
        return {"error": "Set HF_TOKEN env in Render", "echo": r.prompt}
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    url = f"https://api-inference.huggingface.co/models/{MODEL}"
    resp = requests.post(url, headers=headers, json={"inputs": r.prompt, "parameters": {"max_new_tokens": r.max_tokens}}, timeout=60)
    return {"result": resp.json()}

@app.post("/v1/chat/completions")
def chat(payload: dict):
    # OpenAI-compatible wrapper for your sidecar/tools
    msgs = payload.get("messages", [])
    prompt = "\n".join([m.get("content","") for m in msgs])
    return generate(Req(prompt=prompt))
