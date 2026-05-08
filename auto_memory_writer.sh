#!/bin/bash
# 小海虾自动记忆写入（每30分钟由 sync_controller 调用）
# 原理：agent 主动向 pending_memory.json 追加重要记忆，sync 时合并推送

PENDING_FILE="/root/.openclaw/workspace/coordination/pending_memory.json"
COORD_FILE="/root/.openclaw/workspace/coordination/memory.json"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [auto-memory] $*" >&2; }

# 读取待记忆队列
read_pending() {
    if [[ -f "$PENDING_FILE" ]]; then
        cat "$PENDING_FILE"
    else
        echo "[]"
    fi
}

# 写入最终记忆文件（追加到 coordination/memory.json）
merge_to_memory() {
    local pending="$1"
    local count=$(echo "$pending" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
    
    if [[ "$count" == "0" ]] || [[ -z "$pending" ]] || [[ "$pending" == "[]" ]]; then
        log "无待记忆内容，跳过"
        return
    fi
    
    log "待记忆 $count 条，开始合并..."
    
    # 读取现有记忆
    local existing="{\"version\":\"1.0\",\"entries\":[]}"
    if [[ -f "$COORD_FILE" ]]; then
        existing=$(cat "$COORD_FILE")
    fi
    
    # 合并（去重 + 追加）
    local merged
    merged=$(python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone(timedelta(hours=8))).isoformat()
existing = json.loads('''$existing''')
pending = json.loads('''$pending''')

# 去重：检查 content 前80字是否已存在
existing_previews = set(e.get('content','')[:80] for e in existing.get('entries',[]))
added = 0
for p in pending:
    p['synced_at'] = now
    p['local_mtime'] = now
    preview = p.get('content','')[:80]
    if preview not in existing_previews:
        existing['entries'].append(p)
        existing_previews.add(preview)
        added += 1

print(json.dumps(existing, ensure_ascii=False, indent=2))
" 2>&1)
    
    echo "$merged" > "$COORD_FILE"
    log "合并完成，新增 $added 条记忆（总计 $(echo "$merged" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['entries']))") 条）"
    
    # 清空待记忆队列
    echo "[]" > "$PENDING_FILE"
}

# 主动写入一条记忆（agent 调用）
write_memory() {
    local agent="$1"
    local content="$2"
    local mtype="${3:-manual}"
    
    if [[ -z "$content" ]]; then
        echo "用法: auto_memory_writer.sh write <agent> <content> [type]"
        return 1
    fi
    
    local now
    now=$(python3 -c "from datetime import datetime,timezone,timedelta; print(datetime.now(timezone(timedelta(hours=8))).isoformat())")
    
    local entry
    entry=$(python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta
entry = {
    'shrimp': '$agent',
    'type': '$mtype',
    'source': '${agent}_manual',
    'content': '''$content''',
    'synced_at': '$now',
    'local_mtime': '$now'
}
print(json.dumps(entry, ensure_ascii=False))
" 2>&1)
    
    # 追加到待队列
    if [[ ! -f "$PENDING_FILE" ]]; then
        echo "[]" > "$PENDING_FILE"
    fi
    
    local pending_current
    pending_current=$(cat "$PENDING_FILE" 2>/dev/null)
    if [[ -z "$pending_current" ]]; then
        pending_current="[]"
    fi
    
    local updated
    updated=$(python3 << PYEOF
import json
try:
    pending = json.loads('''$pending_current''')
except:
    pending = []
entry = {
    "shrimp": "$agent",
    "type": "$mtype",
    "source": "${agent}_manual",
    "content": """$content""",
    "synced_at": """$now""",
    "local_mtime": """$now"""
}
pending.append(entry)
print(json.dumps(pending, ensure_ascii=False))
PYEOF
)
    
    echo "$updated" > "$PENDING_FILE"
    log "写入记忆: ${content:0:60}..."
}

case "${1:-check}" in
    check|run)
        pending=$(read_pending)
        merge_to_memory "$pending"
        ;;
    write)
        write_memory "$2" "$3" "${4:-manual}"
        ;;
    status)
        count=$(python3 -c "print(len(json.load(open('$PENDING_FILE'))))" 2>/dev/null)
        echo "待记忆: $count 条"
        ;;
    *)
        echo "用法: $0 {check|write <agent> <content> [type]|status}"
        ;;
esac
