#!/usr/bin/env python3
"""
图片自动分析脚本 v2
监控 /root/.openclaw/media/inbound/ 目录，新图片自动用 read 工具分析
"""

import os
import json
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# 配置
INBOUND_DIR = Path("/root/.openclaw/media/inbound")
OUTPUT_DIR = Path("/root/.openclaw/workspace/image-analysis")
OPENCLAW_URL = "http://127.0.0.1:20609"
OPENCLAW_TOKEN = "50fe3f3eb9621cf8ff739020ee20a694941996b3545ecf52"
POLL_INTERVAL = 8  # 秒

# 已处理记录（防止重复分析）
PROCESSED_FILE = OUTPUT_DIR / ".processed.json"

def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()

def save_processed(names):
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(names), f)

def analyze_via_openclaw(image_path):
    """通过 OpenClaw gateway 调用 read 工具分析图片"""
    # 使用 gateway 的 agent tool call 接口
    url = f"{OPENCLAW_URL}/api/agent/call"
    
    payload = {
        "tool": "read",
        "args": {
            "path": str(image_path)
        },
        "token": OPENCLAW_TOKEN
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 200:
            result = resp.json()
            return result.get('result', str(result)[:500])
        else:
            return f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return f"调用失败: {e}"

def process_image(image_path):
    """处理单张图片"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = image_path.name
    size = image_path.stat().st_size
    
    print(f"[{ts}] 📷 分析新图片: {filename} ({size//1024}KB)")
    
    analysis = analyze_via_openclaw(image_path)
    
    # 写入结果文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{date_str}.md"
    
    entry = f"""## {ts} - {filename}

**文件**: `{image_path.name}`
**路径**: `{image_path}`
**大小**: {size//1024}KB

### 分析结果

{analysis}

---
"""
    
    with open(output_file, 'a') as f:
        f.write(entry)
    
    print(f"[{ts}] ✅ 完成 → {output_file}")
    return True

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    processed = load_processed()
    
    print(f"🚀 图片分析守护进程启动 v2")
    print(f"📁 监控目录: {INBOUND_DIR}")
    print(f"📝 结果输出: {OUTPUT_DIR}")
    print(f"🔗 Gateway: {OPENCLAW_URL}")
    print(f"⏱️ 轮询间隔: {POLL_INTERVAL}秒")
    print("-" * 50)
    
    while True:
        try:
            if not INBOUND_DIR.exists():
                print(f"⚠️ 目录不存在: {INBOUND_DIR}")
                time.sleep(POLL_INTERVAL)
                continue
            
            for entry in INBOUND_DIR.iterdir():
                if entry.is_file() and entry.stat().st_size > 5000:
                    # 检查是否是图片
                    if entry.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                        mtime = int(entry.stat().st_mtime)
                        key = f"{entry.name}:{mtime}"
                        
                        if key not in processed:
                            # 等待文件写入稳定
                            time.sleep(2)
                            size1 = entry.stat().st_size
                            time.sleep(2)
                            size2 = entry.stat().st_size
                            
                            if abs(size1 - size2) < 500:  # 大小稳定
                                success = process_image(entry)
                                if success:
                                    processed.add(key)
                                    save_processed(processed)
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
