#!/usr/bin/env python3
"""
OpenClaw Smart Router v2.1
Triple model parallel: MiniMax + GLM-4.7 + GLM-4
"""
import urllib.request, json, time, re, concurrent.futures
from typing import List, Dict, Tuple

API_CONFIG = {
    "minimax": {"url": "https://df.dawnloadai.com:9888/v1/chat/completions"},
    "zhipu": {"url": "https://open.bigmodel.cn/api/paas/v4/chat/completions"}
}
MODELS = [
    {"id": "MiniMax-M2.7-highspeed", "provider": "minimax", "name": "MiniMax"},
    {"id": "glm-4.7-flash", "provider": "zhipu", "name": "GLM-4.7"},
    {"id": "glm-4-flash", "provider": "zhipu", "name": "GLM-4"},
]

def get_key(provider):
    with open("/root/.openclaw/openclaw.json") as f:
        return json.load(f)["models"]["providers"][provider]["apiKey"]

def check_health(model, timeout=8):
    s = time.time()
    try:
        api_key = get_key(model["provider"])
        payload = {"model": model["id"], "messages": [{"role": "user", "content": "ok"}], "max_tokens": 3}
        req = urllib.request.Request(
            API_CONFIG[model["provider"]]["url"],
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout):
            return {"model_id": model["id"], "name": model["name"], "healthy": True, "latency": round(time.time()-s, 3)}
    except Exception as e:
        return {"model_id": model["id"], "name": model["name"], "healthy": False, "latency": round(time.time()-s, 3), "error": str(e)[:50]}

def health_all():
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELS)) as ex:
        futures = {ex.submit(check_health, m): m for m in MODELS}
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            results[r["model_id"]] = r
    return results

def call_model(model_id, messages, max_tokens=2000):
    for m in MODELS:
        if m["id"] == model_id:
            provider = m["provider"]
            break
    api_key = get_key(provider)
    url = API_CONFIG[provider]["url"]
    s = time.time()
    payload = {"model": model_id, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["choices"][0]["message"]["content"], round(time.time()-s, 2)

def multi_call(model_ids, messages):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(model_ids)) as ex:
        futures = {ex.submit(call_model, mid, messages): mid for mid in model_ids}
        for f in concurrent.futures.as_completed(futures):
            mid = futures[f]
            try:
                reply, lat = f.result()
                results.append({"model_id": mid, "reply": reply, "latency": lat, "success": True})
            except Exception as e:
                results.append({"model_id": mid, "reply": f"Error: {str(e)[:50]}", "latency": 0, "success": False})
    return results

def fuse(results):
    ok = [r for r in results if r.get("success")]
    if not ok:
        return "All models failed"
    ok.sort(key=lambda x: len(x.get("reply","")), reverse=True)
    best = ok[0]
    names = ", ".join([r["model_id"] for r in ok])
    hdr = f"[Multi-model | {len(ok)} candidates | using {best['model_id']} | {best['latency']}s]"
    if len(ok) > 1:
        return hdr + "\nOthers: " + names + "\n\n" + best["reply"] + f"\n\n--- Models: {names} ---"
        return hdr + "\n" + best["reply"] + f"\n\n--- Models: {best['model_id']} ---"

def process(text, history=None):
    history = history or []
    msgs = history + [{"role": "user", "content": text}]
    health = health_all()
    avail = [(mid, info) for mid, info in health.items() if info.get("healthy")]
    if not avail:
        return "All models unavailable"
    avail.sort(key=lambda x: x[1].get("latency", 999))
    if len(avail) > 1:
        mids = [mid for mid, _ in avail]
        return fuse(multi_call(mids, msgs))
    best_id = avail[0][0]
    best_name = avail[0][1]["name"]
    try:
        reply, lat = call_model(best_id, msgs)
        return f"[{best_name} | {lat}s]\n\n{reply}\n\n--- Model: {best_id} ---"
    except Exception as e:
        return f"Error: {str(e)[:100]}"

def main():
    print("=== Smart Router v2.1 ===\n")
    h = health_all()
    for mid, info in h.items():
        s = "OK" if info.get("healthy") else "FAIL"
        lat = f"{info.get('latency',0):.2f}s" if info.get("healthy") else info.get("error","")[:20]
        print(f"  {s} {info['name']}: {lat}")
    print()
    for q in ["hi", "how is weather", "python quicksort", "apple vs orange"]:
        print(f"Q: {q}")
        print(process(q))
        print()

if __name__ == "__main__":
    main()