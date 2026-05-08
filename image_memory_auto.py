#!/usr/bin/env python3
"""
image_memory_auto.py - 小屿图片分析结果自动存档
当小屿分析完图片后，结果自动写入 coordination/image_memory.json
"""

import os
import json
from datetime import datetime, timezone, timedelta

IMAGE_MEMORY_FILE = "/root/.openclaw/workspace/coordination/image_memory.json"
COORD_MEMORY_FILE = "/root/.openclaw/workspace/coordination/memory.json"

def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def write_image_memory(content: str, image_path: str = "", tags: list = None):
    """写入一条图片记忆"""
    entry = {
        "shrimp": "xiaoyu",
        "type": "image_analysis",
        "source": "xiaoyu_auto",
        "content": content,
        "image_path": image_path,
        "tags": tags or ["图片分析"],
        "synced_at": now_iso(),
        "local_mtime": now_iso()
    }
    
    # 读取或初始化
    data = {"version": "1.0", "entries": []}
    if os.path.exists(IMAGE_MEMORY_FILE):
        try:
            with open(IMAGE_MEMORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            pass
    
    # 去重
    existing = {e.get('content', '')[:80]: True for e in data.get('entries', [])}
    preview = content[:80]
    if preview not in existing:
        data["entries"].append(entry)
        with open(IMAGE_MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    return False

def get_latest(n: int = 5):
    """获取最近 N 条图片记忆"""
    if not os.path.exists(IMAGE_MEMORY_FILE):
        return []
    try:
        with open(IMAGE_MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("entries", [])[-n:]
    except:
        return []

def merge_to_main_memory():
    """合并图片记忆到主 memory.json"""
    if not os.path.exists(IMAGE_MEMORY_FILE):
        return 0
    
    with open(IMAGE_MEMORY_FILE, 'r', encoding='utf-8') as f:
        img_data = json.load(f)
    
    img_entries = img_data.get("entries", [])
    if not img_entries:
        return 0
    
    # 读取主记忆
    main_data = {"version": "1.0", "entries": []}
    if os.path.exists(COORD_MEMORY_FILE):
        try:
            with open(COORD_MEMORY_FILE, 'r', encoding='utf-8') as f:
                main_data = json.load(f)
        except:
            pass
    
    # 去重合并
    existing_previews = {e.get('content', '')[:80] for e in main_data.get("entries", [])}
    added = 0
    for entry in img_entries:
        preview = entry.get('content', '')[:80]
        if preview not in existing_previews:
            main_data["entries"].append(entry)
            existing_previews.add(preview)
            added += 1
    
    if added > 0:
        with open(COORD_MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, ensure_ascii=False, indent=2)
    
    return added

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "write":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
        path = sys.argv[3] if len(sys.argv) > 3 else ""
        tags = sys.argv[4].split(",") if len(sys.argv) > 4 else None
        if content:
            ok = write_image_memory(content, path, tags)
            print(f"写入图片记忆: {'成功' if ok else '重复跳过'}")
        else:
            print("用法: python3 image_memory_auto.py write <内容> [图片路径] [标签]")
    
    elif cmd == "latest":
        entries = get_latest(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
        for e in entries:
            print(f"[{e.get('synced_at','')[:10]}] {e.get('content','')[:80]}...")
    
    elif cmd == "merge":
        added = merge_to_main_memory()
        print(f"合并 {added} 条到主记忆")
    
    elif cmd == "status":
        entries = get_latest(10)
        print(f"图片记忆库: {len(entries)} 条")
        for e in entries[-5:]:
            print(f"  - {e.get('content','')[:60]}...")
    
    else:
        print("用法: image_memory_auto.py {write|latest|merge|status}")