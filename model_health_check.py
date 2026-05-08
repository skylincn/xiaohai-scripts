#!/usr/bin/env python3
"""
模型测活检测脚本 v1.0
在发消息前先检测模型是否可用，避免无效等待
"""

import urllib.request
import json
import time
import concurrent.futures

# 从配置文件读取 API Key
def get_api_key(provider: str) -> str:
    with open('/root/.openclaw/openclaw.json') as f:
        config = json.load(f)
    return config['models']['providers'][provider]['apiKey']

# 模型配置
MODELS = [
    {"id": "MiniMax-M2.7-highspeed", "provider": "minimax", "name": "MiniMax-M2.7"},
    {"id": "Kimi-K2.6", "provider": "kimi", "name": "Kimi-K2.6"},
    {"id": "glm-4-flash", "provider": "zhipu", "name": "GLM-4-Flash"},
]

API_ENDPOINTS = {
    "minimax": "https://df.dawnloadai.com:9888/v1/chat/completions",
    "kimi": "https://df.dawnloadai.com:9888/v1/chat/completions",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
}


def check_health(model: dict, timeout: int = 8) -> dict:
    """检测单个模型是否可用"""
    start = time.time()
    model_id = model["id"]
    provider = model["provider"]
    url = API_ENDPOINTS[provider]
    
    try:
        api_key = get_api_key(provider)
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "ok"}],
            "max_tokens": 3,
            "temperature": 0.1
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.time() - start
            result = json.load(resp)
            if resp.status == 200 and result.get("choices"):
                return {
                    "model": model_id,
                    "name": model["name"],
                    "healthy": True,
                    "latency": round(elapsed, 3),
                    "error": None
                }
            return {
                "model": model_id,
                "name": model["name"],
                "healthy": False,
                "latency": elapsed,
                "error": "Empty response"
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "model": model_id,
            "name": model["name"],
            "healthy": False,
            "latency": round(elapsed, 3),
            "error": str(e)[:50]
        }


def check_all() -> list:
    """并行检测所有模型，返回按速度排序的结果"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(MODELS)) as executor:
        futures = {executor.submit(check_health, m): m for m in MODELS}
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            results.append(r)
    
    # 按延迟排序
    results.sort(key=lambda x: x["latency"] if x["healthy"] else 999)
    return results


def main():
    print("=== 模型测活检测 ===")
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = check_all()
    
    print("检测结果（按速度排序）:")
    print("-" * 50)
    
    healthy_count = 0
    for r in results:
        status = "✅ 可用" if r["healthy"] else "❌ 不可用"
        latency_str = f"{r['latency']:.3f}s" if r["healthy"] else "-"
        
        if r["healthy"]:
            healthy_count += 1
            print(f"  {status} | 延迟: {latency_str:>8} | {r['name']}")
        else:
            print(f"  {status} | 错误: {r['error']:>15} | {r['name']}")
    
    print("-" * 50)
    print(f"可用模型: {healthy_count}/{len(results)}")
    print()
    
    if healthy_count > 0:
        best = next(r for r in results if r["healthy"])
        print(f"推荐模型: {best['name']}（延迟 {best['latency']:.3f}s）")
    else:
        print("⚠️ 所有模型不可用，请检查网络")


if __name__ == "__main__":
    main()
