#!/usr/bin/env python3
"""
GLM-4.1V 识图 Wrapper
用法: python3 glm_vision.py <图片路径> [提示词]
示例: python3 glm_vision.py /path/to/photo.jpg "详细描述这张图片"
"""

import sys
import os
import json
import base64
import urllib.request
import urllib.error

API_KEY = "8e7b292043eb499a9dfd2e26db50f7aa.UO1pbaNRNjXN9voD"
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL = "glm-4.1v-thinking-flash"


def describe_image(image_path: str, prompt: str = "详细描述这张图片的内容") -> str:
    """调用智谱 GLM-4.1V API 识图"""
    
    # 读取图片并 base64 编码
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    # 构造请求
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]
            }
        ],
        "max_tokens": 2048
    }
    
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            elif "error" in data:
                return f"[API Error] {json.dumps(data['error'], ensure_ascii=False)}"
            else:
                return f"[Unexpected Response] {json.dumps(data, ensure_ascii=False)}"
    except urllib.error.HTTPError as e:
        body = e.read().decode() if hasattr(e, 'read') else ''
        return f"[HTTP {e.code}] {body[:200]}"
    except Exception as e:
        return f"[Error] {type(e).__name__}: {str(e)}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 glm_vision.py <image_path> [prompt]", file=sys.stderr)
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else "详细描述这张图片的内容"
    
    if not os.path.exists(image_path):
        print(f"[Error] File not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    
    result = describe_image(image_path, prompt)
    print(result)
