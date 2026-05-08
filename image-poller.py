#!/usr/bin/env python3
"""
图片轮询脚本 - 由 OpenClaw cron 定期调用
检查 inbound 目录新图片，用 read 工具分析，结果写入文件
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

INBOUND_DIR = Path("/root/.openclaw/media/inbound")
OUTPUT_DIR = Path("/root/.openclaw/workspace/image-analysis")
PROCESSED_FILE = OUTPUT_DIR / ".processed.json"
GATEWAY_TOKEN = "50fe3f3eb9621cf8ff739020ee20a694941996b3545ecf52"

def load_processed():
    if PROCESSED_FILE.exists():
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()

def save_processed(names):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(names), f)

def write_result(image_path, analysis):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"{date_str}.md"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    size = image_path.stat().st_size
    
    entry = f"""## {ts} - {image_path.name}

**文件**: `{image_path.name}`
**路径**: `{image_path}`
**大小**: {size//1024}KB

### 分析结果

{analysis}

---
"""
    
    with open(output_file, 'a') as f:
        f.write(entry)
    
    print(f"✅ 结果已写入: {output_file}")

def main():
    processed = load_processed()
    found_new = False
    
    if not INBOUND_DIR.exists():
        print(f"目录不存在: {INBOUND_DIR}")
        sys.exit(0)
    
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
        
        # 新图片！等待写入完成
        time.sleep(3)
        size1 = entry.stat().st_size
        time.sleep(2)
        size2 = entry.stat().st_size
        
        if abs(size1 - size2) > 1000:
            print(f"文件还在写入，跳过: {entry.name}")
            continue
        
        print(f"📷 发现新图片: {entry.name}")
        found_new = True
        
        # 把图片路径记录下来
        # 由于无法直接调用 read 工具，把任务写入待处理队列
        queue_file = OUTPUT_DIR / ".queue.json"
        queue = []
        if queue_file.exists():
            with open(queue_file) as f:
                queue = json.load(f)
        
        queue.append({
            "path": str(entry.absolute()),
            "key": key,
            "ts": datetime.now().isoformat()
        })
        
        with open(queue_file, 'w') as f:
            json.dump(queue, f, indent=2)
        
        print(f"📝 已加入处理队列: {entry.name}")
    
    if found_new:
        print(f"\n🔔 新图片已加入队列，将由主 agent 处理")
        print(f"📋 队列文件: {queue_file}")
        print(f"📖 分析结果: {OUTPUT_DIR}/YYYY-MM-DD.md")
    else:
        print("没有发现新图片")

if __name__ == "__main__":
    main()
