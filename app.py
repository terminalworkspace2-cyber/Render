import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json, time, re

app = FastAPI()
llm = None
try:
    from llama_cpp import Llama
    # Download model on first start
    model_path = "LFM2-350M-Q4_K_M.gguf"
    if not os.path.exists(model_path):
        import urllib.request
        print("downloading model...")
        urllib.request.urlretrieve("https://huggingface.co/LiquidAI/LFM2-350M-GGUF/resolve/main/LFM2-350M-Q4_K_M.gguf", model_path)
    llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
    print("model loaded")
except Exception as e:
    print(f"model failed: {e}")

class Req(BaseModel):
    messages: list
    max_tokens: int = 200
    stream: bool = False

def run_tool(name, args):
    if name=="calc":
        return json.dumps({"result": eval(args.get("expression","0"))})
    if name=="get_time":
        return json.dumps({"time": time.ctime()})
    return json.dumps({"error":"unknown"})

@app.get("/v1/models")
def models():
    return {"object":"list","data":[{"id":"liquid-lfm2-350m","object":"model"}]}

@app.post("/v1/chat/completions")
def chat(req: Req):
    last = req.messages[-1]["content"].lower() if req.messages else ""
    m = re.search(r'(\d+\s*[\+\-\*/]\s*\d+)', last)
    if "calc" in last and m:
        res = run_tool("calc", {"expression": m.group(1)})
        return {"choices":[{"message":{"role":"assistant","content":f"The result is {json.loads(res)['result']} (calculated by tool)","tool_calls":[{"id":"1","type":"function","function":{"name":"calc","arguments":"{}"}}]},"finish_reason":"tool_calls"}],"tool_result":res}
    if "time" in last:
        res = run_tool("get_time", {})
        return {"choices":[{"message":{"role":"assistant","content":f"Tool get_time result: {res}","tool_calls":[{"id":"1","type":"function","function":{"name":"get_time","arguments":"{}"}}]},"finish_reason":"tool_calls"}],"tool_result":res}
    if llm is None:
        return {"choices":[{"message":{"role":"assistant","content":"model not loaded yet"}}]}
    prompt = ""
    for msg in req.messages:
        prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    out = llm(prompt, max_tokens=req.max_tokens, stop=["<|im_end|>"])
    text = out["choices"][0]["text"]
    return {"choices":[{"message":{"role":"assistant","content":text},"finish_reason":"stop"}]}
