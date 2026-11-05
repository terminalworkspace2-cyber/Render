import requests, urllib.parse, time, uuid, json, math, datetime, re
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

def tool_get_time():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
    return f"Current time in Nigeria (WAT): {now.strftime('%Y-%m-%d %H:%M:%S')}"
def tool_calculate(expression: str):
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            return "Error: only numbers and +-*/() allowed"
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"
def tool_get_weather(city: str):
    try:
        r = requests.get(f"https://wttr.in/{city}?format=%C+%t", timeout=10)
        return f"Weather in {city}: {r.text}"
    except:
        return f"Could not get weather for {city}"

TOOLS_DEF = [
    {"type": "function", "function": {"name": "get_time", "description": "Get current time in Nigeria", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "calculate", "description": "Calculate math", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Get weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
]
def run_tool(name, args):
    if name == "get_time": return tool_get_time()
    if name == "calculate": return tool_calculate(args.get("expression",""))
    if name == "get_weather": return tool_get_weather(args.get("city","Lagos"))
    return "Tool not found"
def call_pollinations(prompt: str):
    q = urllib.parse.quote(prompt)
    r = requests.get(f"https://text.pollinations.ai/{q}?model=openai", timeout=60)
    return r.text
def new_id(): return f"chatcmpl-{uuid.uuid4().hex[:24]}"

class Req(BaseModel):
    prompt: str

# --- GET + POST BOTH ---
@app.get("/")
def root_get(): return {"status": "ok", "mode": "openai-compatible", "features": ["POST", "tool_calls", "streaming", "id", "object"]}
@app.post("/")
def root_post(payload: dict = {}): return {"status": "ok", "mode": "openai-compatible", "received": payload, "id": new_id(), "object": "chat.completion"}

@app.get("/health")
def health_get(): return {"status": "ok"}
@app.post("/health")
def health_post(payload: dict = {}): return {"status": "ok", "id": new_id(), "object": "health.check"}

@app.post("/generate")
def generate(r: Req): return {"id": new_id(), "object": "text_completion", "result": call_pollinations(r.prompt)}
@app.get("/generate")
def generate_get(prompt: str = "Hello"): return {"id": new_id(), "object": "text_completion", "result": call_pollinations(prompt)}

# --- POST TOOLS DIRECT ---
@app.post("/v1/tools/call")
@app.post("/tools/call")
@app.post("/tools")
def tools_call(payload: dict):
    # POST {"name":"calculate","arguments":{"expression":"2+2"}}
    name = payload.get("name") or payload.get("tool") or payload.get("function", {}).get("name")
    args = payload.get("arguments") or payload.get("args") or payload.get("function", {}).get("arguments") or {}
    if isinstance(args, str):
        try: args = json.loads(args)
        except: args = {"expression": args}
    result = run_tool(name, args)
    return {"id": new_id(), "object": "tool_call.result", "name": name, "arguments": args, "result": result}

@app.get("/v1/tools")
def tools_list(): return {"object": "list", "data": TOOLS_DEF}

# --- MAIN CHAT - POST ---
@app.post("/v1/chat/completions")
@app.post("/v1/completions")
@app.post("/chat/completions")
@app.post("/chat")
def chat(payload: dict):
    msgs = payload.get("messages", [])
    if not msgs and payload.get("prompt"):
        msgs = [{"role": "user", "content": payload.get("prompt")}]
    stream = payload.get("stream", False)
    model = payload.get("model", "pollinations-openai")
    prompt = "\n".join([f"{m.get('role')}: {m.get('content','')}" for m in msgs])
    last = msgs[-1].get("content","") if msgs else ""
    low = last.lower()
    tool_call = None
    if "time" in low and ("what" in low or "current" in low):
        tool_call = {"name": "get_time", "args": {}}
    elif "calculate" in low or "calc" in low or ("what is" in low and any(c in low for c in ["+", "*", "/"])):
        m = re.search(r"([0-9\+\-\*/\(\)\. ]+)", last)
        if m: tool_call = {"name": "calculate", "args": {"expression": m.group(1).strip()}}
    elif "weather" in low:
        m = re.search(r"weather in (\w+)", low) or re.search(r"weather (\w+)", low)
        city = m.group(1) if m else "Lagos"
        tool_call = {"name": "get_weather", "args": {"city": city}}
    cid = new_id(); created = int(time.time())
    if stream:
        def gen():
            if tool_call:
                chunk = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"role": "assistant", "content": None, "tool_calls": [{"index": 0, "id": f"call_{uuid.uuid4().hex[:8]}", "type": "function", "function": {"name": tool_call["name"], "arguments": json.dumps(tool_call["args"])}}]}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk)}\n\n"
                result = run_tool(tool_call["name"], tool_call["args"])
                chunk2 = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"content": f"\nTool result: {result}"}, "finish_reason": "tool_calls"}]}
                yield f"data: {json.dumps(chunk2)}\n\n"
                yield "data: [DONE]\n\n"; return
            text = call_pollinations(prompt)
            for word in text.split(" "):
                chunk = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"role": "assistant", "content": word + " "}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk)}\n\n"
            final = {"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            yield f"data: {json.dumps(final)}\n\n"; yield "data: [DONE]\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")
    if tool_call:
        result = run_tool(tool_call["name"], tool_call["args"])
        final_text = f"I used tool `{tool_call['name']}`. Result: {result}"
        return {"id": cid, "object": "chat.completion", "created": created, "model": model, "choices": [{"index": 0, "message": {"role": "assistant", "content": final_text, "tool_calls": [{"id": f"call_{uuid.uuid4().hex[:8]}", "type": "function", "function": {"name": tool_call["name"], "arguments": json.dumps(tool_call["args"])}}]}, "finish_reason": "tool_calls"}], "usage": {"prompt_tokens": len(prompt), "completion_tokens": len(final_text), "total_tokens": len(prompt)+len(final_text)}}
    text = call_pollinations(prompt)
    return {"id": cid, "object": "chat.completion", "created": created, "model": model, "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": len(prompt), "completion_tokens": len(text), "total_tokens": len(prompt)+len(text)}}

@app.get("/v1/models")
@app.post("/v1/models")
def models(): return {"object": "list", "data": [{"id": "pollinations-openai", "object": "model", "created": int(time.time()), "owned_by": "pollinations"}]}
