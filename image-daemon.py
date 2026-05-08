#!/usr/bin/env python3
"""
定期检查 inbound 目录，发现新图片则通过 gateway API 触发 agent 分析
"""

import os
import sys
import json
import time
import websocket
import threading
from datetime import datetime
from pathlib import Path

INBOUND_DIR = Path("/root/.openclaw/media/inbound")
OUTPUT_DIR = Path("/root/.openclaw/workspace/image-analysis")
PROCESSED_FILE = OUTPUT_DIR / ".processed.json"
GATEWAY_URL = "ws://127.0.0.1:20609"
TOKEN = "50fe3f3eb9621cf8ff739020ee20a694941996b3545ecf52"
POLL_INTERVAL = 5  # 秒

def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()

def save_processed(names):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(names), f)

def get_ws_connection():
    ws = websocket.WebSocket()
    ws.connect(GATEWAY_URL, 
               header=[f"Authorization: Bearer {TOKEN}"],
               subprotocols=["json"]
    )
    return ws

def ws_send(ws, payload, msg_id):
    ws.send(json.dumps(payload))

def ws_recv(ws):
    return json.loads(ws.recv())

def call_tool(ws, tool_name, tool_args, msg_id):
    """通过 WebSocket JSON-RPC 调用 gateway 工具"""
    payload = {
        "jsonrpc": "2.0",
        "id": msg_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": tool_args
        }
    }
    ws_send(ws, payload, msg_id)
    
    # 等待响应
    while True:
        resp = ws_recv(ws)
        if resp.get("id") == msg_id:
            return resp.get("result", resp)

def spawn_read_session(image_path, msg_id_base):
    """通过 gateway WebSocket 生成一个新的 agent session 来读取图片"""
    ws = websocket.WebSocket()
    try:
        ws.connect(GATEWAY_URL,
                   header=[f"Authorization: Bearer {TOKEN}"],
                   subprotocols=["json"])
        
        # 创建一个新的 agent session
        create_payload = {
            "jsonrpc": "2.0",
            "id": msg_id_base,
            "method": "sessions/spawn",
            "params": {
                "kind": "agent",
                "model": "minimax/MiniMax-M2.7-highspeed",
                "prompt": f"""请读取图片文件: {image_path}

使用 read 工具分析这张图片，然后用 text 写入工具把分析结果保存到:
/root/.openclaw/workspace/image-analysis/{datetime.now().strftime('%Y-%m-%d')}.md

格式:
## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {Path(image_path).name}

分析内容:
[在这里写入 read 工具的分析结果]
"""
            }
        }
        ws.send(json.dumps(create_payload))
        
        # 等待响应
        ws.settimeout(5)
        try:
            resp = ws.recv()
            print(f"Session spawn response: {resp[:200]}")
        except:
            pass
        
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ws.close()

def process_image(image_path):
    """处理单张图片 - 通过 gateway 工具调用"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = Path(image_path).name
    size = Path(image_path).stat().st_size
    
    print(f"[{ts}] 📷 分析: {filename} ({size//1024}KB)")
    
    # 尝试通过 gateway WebSocket 调用 read 工具
    try:
        ws = get_ws_connection()
        msg_id = int(time.time() * 1000) % 100000
        
        # 读取图片
        read_result = call_tool(ws, "read", {"path": image_path}, msg_id)
        print(f"Read result: {str(read_result)[:300]}")
        
        ws.close()
        
        # 写入结果
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_file = OUTPUT_DIR / f"{date_str}.md"
        
        entry = f"""## {ts} - {filename}

**文件**: `{filename}`
**路径**: `{image_path}`
**大小**: {size//1024}KB

### 分析结果

{read_result.get('content', read_result) if isinstance(read_result, dict) else read_result}

---
"""
        
        with open(output_file, 'a') as f:
            f.write(entry)
        
        print(f"[{ts}] ✅ 已写入: {output_file}")
        return True
        
    except Exception as e:
        print(f"处理失败: {e}")
        # 降级：写入待处理队列
        queue_file = OUTPUT_DIR / ".queue.json"
        queue = []
        if queue_file.exists():
            with open(queue_file) as f:
                queue = json.load(f)
        
        queue.append({
            "path": str(image_path),
            "ts": ts,
            "error": str(e)
        })
        
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        
        return False

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    processed = load_processed()
    
    print(f"🚀 图片守护进程启动")
    print(f"📁 监控: {INBOUND_DIR}")
    print(f"📝 输出: {OUTPUT_DIR}")
    print("-" * 50)
    
    while True:
        try:
            if not INBOUND_DIR.exists():
                time.sleep(POLL_INTERVAL)
                continue
            
            for entry in INBOUND_DIR.iterdir():
                if not entry.is_file():
                    continue
                
                if entry.stat().st_size < 5000:
                    continue
                    
                if entry.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                    continue
                
                mtime = int(entry.stat().st_mtime)
                key = f"{entry.name}:{mtime}"
                
                if key in processed:
                    continue
                
                # 新图片 - 等待稳定
                time.sleep(3)
                size1 = entry.stat().st_size
                time.sleep(2)
                size2 = entry.stat().st_size
                
                if abs(size1 - size2) > 1000:
                    continue
                
                # 处理
                success = process_image(entry)
                if success:
                    processed.add(key)
                    save_processed(processed)
                    
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
