#!/bin/bash
# 多 Agent 智能同步控制器 v1.1
# 
# 功能：
#   - 每 30 分钟检查是否需要同步
#   - 1小时无任何活动 → 暂停同步
#   - 有活动 → 立即同步 + 恢复正常调度
#
# Cron: */30 * * * *（每30分钟）
# NAS状态文件: /var/services/homes/skyyz/shared/coordination/sync_state.json

NAS_HOST="152.136.61.172"
NAS_SSH_PORT="7422"
NAS_USER="skyyz"
NAS_PASS="Lin998007"

# 协调目录
NAS_COORD="/var/services/homes/skyyz/shared/coordination"
STATE_FILE="$NAS_COORD/sync_state.json"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [sync-ctrl] $*" >&2; }

# 获取当前 UTC+8 时间
now_utc8() {
    python3 -c "from datetime import datetime,timezone,timedelta; print(datetime.now(timezone(timedelta(hours=8))).isoformat())"
}

# 读取状态文件
get_state() {
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
        "cat $STATE_FILE 2>/dev/null" 2>/dev/null || echo '{"last_activity":{},"last_sync":"","sync_paused":false}'
}

# 写状态文件
put_state() {
    local json="$1"
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
        "cat > $STATE_FILE" <<< "$json" 2>/dev/null
}

# 记录活动（被 agent 调用）
record_activity() {
    local agent="$1"
    local ts=$(now_utc8)
    
    log "记录活动: agent=$agent at $ts"
    
    local state=$(get_state)
    local new_state=$(python3 -c "
import json, sys
state = json.loads('''$state''')
ts = '$ts'
agent = '$agent'

if 'last_activity' not in state:
    state['last_activity'] = {}
state['last_activity'][agent] = ts

if state.get('sync_paused', False):
    state['sync_paused'] = False
    print('恢复同步 (因 ' + agent + ' 有活动)', file=sys.stderr)

print(json.dumps(state))
" 2>&1)
    
    put_state "$new_state"
    log "活动记录完成"
}

# 主检查逻辑
check_and_sync() {
    local current_state=$(get_state)
    local now=$(now_utc8)
    
    log "=== 开始检查 ==="
    log "当前状态: $current_state"
    
    # 检查最近1小时是否有活动
    local need_sync_result=$(python3 -c "
import json, sys
from datetime import datetime, timezone, timedelta

try:
    state = json.loads('''$current_state''')
except:
    print('状态解析失败')
    sys.exit(0)

now_str = '$now'
now_dt = datetime.fromisoformat(now_str.replace('Z', '+00:00'))
cutoff = now_dt - timedelta(hours=1)

last_act = state.get('last_activity', {})
print('活动记录:', last_act)

if not last_act:
    print('无活动记录，需同步')
    sys.exit(0)

for agent, ts_str in last_act.items():
    try:
        ts_dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        if ts_dt >= cutoff:
            print(agent + ' 在1小时内有活动，需同步')
            sys.exit(0)
    except Exception as e:
        pass

print('1小时内无活动，暂停同步')
sys.exit(1)
" 2>&1)
    
    local reason="$need_sync_result"
    log "检查结果: $reason"
    
    if echo "$need_sync_result" | grep -q "需同步"; then
        log "触发同步，执行 memory_sync_push.sh"
        
        local new_state=$(python3 -c "
import json
state = json.loads('''$current_state''')
state['last_sync'] = '$now'
state['sync_paused'] = False
print(json.dumps(state))
" 2>&1)
        put_state "$new_state"
        
        bash /root/.openclaw/workspace/scripts/memory_sync_push.sh
        log "同步完成"
    else
        log "暂停同步（1小时无活动）"
        local new_state=$(python3 -c "
import json
state = json.loads('''$current_state''')
state['sync_paused'] = True
state['pause_reason'] = '1小时无活动'
print(json.dumps(state))
" 2>&1)
        put_state "$new_state"
    fi
}

# =====================
# 入口
# =====================
case "${1:-check}" in
    activity)
        record_activity "${2:-unknown}"
        ;;
    check)
        check_and_sync
        ;;
    status)
        get_state
        ;;
    force-sync)
        log "强制同步"
        bash /root/.openclaw/workspace/scripts/memory_sync_push.sh
        ;;
    *)
        echo "用法: $0 {activity <agent>|check|status|force-sync}"
        ;;
esac