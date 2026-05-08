#!/usr/bin/env python3
"""
auto_memory_writer.py - 小海虾自动记忆写入 v2.0
支持 write / check / status 三种模式

Agent 调用示例（写入记忆）:
  python3 auto_memory_writer.py write xiaohaixia "记忆内容" manual

Sync 时调用（合并到 memory.json）:
  python3 auto_memory_writer.py check
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta

PENDING_FILE = "/root/.openclaw/workspace/coordination/pending_memory.json"
MEMORY_FILE = "/root/.openclaw/workspace/coordination/memory.json"

def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [auto-memory] {msg}", file=sys.stderr)

def write_memory(agent: str, content: str, mtype: str = "manual"):
    """写入一条记忆到待处理队列"""
    entry = {
        "shrimp": agent,
        "type": mtype,
        "source": f"{agent}_manual",
        "content": content,
        "synced_at": now_iso(),
        "local_mtime": now_iso()
    }
    
    # 读取或初始化待队列
    pending = []
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r', encoding='utf-8') as f:
                pending = json.load(f)
        except:
            pending = []
    
    pending.append(entry)
    
    os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    
    log(f"写入记忆 [{agent}]: {content[:60]}...")

def merge_to_memory():
    """将待记忆队列合并到 memory.json"""
    if not os.path.exists(PENDING_FILE):
        log("无待记忆文件，跳过")
        return
    
    try:
        with open(PENDING_FILE, 'r', encoding='utf-8') as f:
            pending = json.load(f)
    except:
        log("待记忆文件读取失败，跳过")
        return
    
    if not pending:
        log("无待记忆内容，跳过")
        return
    
    log(f"发现 {len(pending)} 条待记忆，开始合并...")
    
    # 读取现有记忆
    existing = {"version": "1.0", "entries": []}
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except:
            pass
    
    # 去重 + 追加
    existing_previews = set(e.get('content', '')[:80] for e in existing.get('entries', []))
    added = 0
    for p in pending:
        p['synced_at'] = now_iso()
        preview = p.get('content', '')[:80]
        if preview not in existing_previews:
            existing['entries'].append(p)
            existing_previews.add(preview)
            added += 1
    
    # 写回 memory.json
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    log(f"合并完成：新增 {added} 条（总计 {len(existing['entries'])} 条）")
    
    # 清空待队列
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

def show_status():
    """显示待记忆队列状态"""
    if not os.path.exists(PENDING_FILE):
        print("待记忆: 0 条")
        return
    
    try:
        with open(PENDING_FILE, 'r', encoding='utf-8') as f:
            pending = json.load(f)
        print(f"待记忆: {len(pending)} 条")
        if pending:
            for i, p in enumerate(pending[:3]):
                print(f"  [{i+1}] [{p.get('shrimp', '?')}] {p.get('content', '')[:60]}...")
            if len(pending) > 3:
                print(f"  ... 还有 {len(pending)-3} 条")
    except Exception as e:
        print(f"状态读取失败: {e}")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if cmd == "write":
        if len(sys.argv) < 4:
            print("用法: python3 auto_memory_writer.py write <agent> <content> [type]", file=sys.stderr)
            sys.exit(1)
        agent = sys.argv[2]
        content = sys.argv[3]
        mtype = sys.argv[4] if len(sys.argv) > 4 else "manual"
        write_memory(agent, content, mtype)
    
    elif cmd == "check":
        merge_to_memory()
    
    elif cmd == "status":
        show_status()
    
    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        print("用法: python3 auto_memory_writer.py {write|check|status}")

if __name__ == "__main__":
    main()
