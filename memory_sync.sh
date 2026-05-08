#!/bin/bash
# 🦐 跨平台记忆同步脚本
# 用法: bash memory_sync.sh [push|pull]

NAS_USER="skyyz"
NAS_PASS="Lin998007"
NAS_HOST="152.136.61.172"
NAS_PORT="7422"
NAS_MEMORY_DIR="/var/services/homes/skyyz/shared/memory_pool"
LOCAL_MEMORY_DIR="/root/.openclaw/workspace/memory"
MEMORY_MD="/root/.openclaw/workspace/MEMORY.md"

# SSH 基础命令
SSH_CMD="sshpass -p '$NAS_PASS' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p $NAS_PORT $NAS_USER@$NAS_HOST"

sync_push() {
    echo "=== 推送记忆到 NAS ==="
    # 确保 NAS 目录存在
    eval "$SSH_CMD" "mkdir -p $NAS_MEMORY_DIR" 2>/dev/null
    
    # 推送 MEMORY.md
    cat "$MEMORY_MD" | eval "$SSH_CMD" "cat > $NAS_MEMORY_DIR/MEMORY.md" 2>/dev/null
    echo "✅ MEMORY.md 已推送"
    
    # 推送今日记忆
    TODAY=$(date +%Y-%m-%d)
    if [ -f "$LOCAL_MEMORY_DIR/$TODAY.md" ]; then
        cat "$LOCAL_MEMORY_DIR/$TODAY.md" | eval "$SSH_CMD" "cat > $NAS_MEMORY_DIR/$TODAY.md" 2>/dev/null
        echo "✅ $TODAY.md 已推送"
    fi
    
    # 生成会话上下文快照
    cat > /tmp/session_context.json << EOF
{
    "lastUpdate": "$(date -Iseconds)",
    "platform": "xiaohaixia",
    "memoryVersion": "$(md5sum $MEMORY_MD | cut -d' ' -f1)",
    "todayNotes": "$TODAY.md"
}
EOF
    cat /tmp/session_context.json | eval "$SSH_CMD" "cat > $NAS_MEMORY_DIR/session_context.json" 2>/dev/null
    echo "✅ 会话上下文已推送"
}

sync_pull() {
    echo "=== 从 NAS 拉取记忆 ==="
    # 拉取 MEMORY.md（如果 NAS 版本更新）
    eval "$SSH_CMD" "cat $NAS_MEMORY_DIR/MEMORY.md 2>/dev/null" > /tmp/MEMORY.md.nas 2>/dev/null
    if [ -s /tmp/MEMORY.md.nas ]; then
        NAS_MD5=$(md5sum /tmp/MEMORY.md.nas | cut -d' ' -f1)
        LOCAL_MD5=$(md5sum $MEMORY_MD | cut -d' ' -f1)
        if [ "$NAS_MD5" != "$LOCAL_MD5" ]; then
            cp /tmp/MEMORY.md.nas $MEMORY_MD
            echo "✅ MEMORY.md 已从 NAS 更新"
        else
            echo "✅ MEMORY.md 已是最新"
        fi
    fi
    
    # 拉取会话上下文
    eval "$SSH_CMD" "cat $NAS_MEMORY_DIR/session_context.json 2>/dev/null" > /tmp/session_context.json 2>/dev/null
    if [ -s /tmp/session_context.json ]; then
        LAST_UPDATE=$(cat /tmp/session_context.json | python3 -c "import json,sys; print(json.load(sys.stdin).get('lastUpdate',''))" 2>/dev/null)
        LAST_PLATFORM=$(cat /tmp/session_context.json | python3 -c "import json,sys; print(json.load(sys.stdin).get('platform',''))" 2>/dev/null)
        echo "✅ 最后更新: $LAST_UPDATE (来自: $LAST_PLATFORM)"
    fi
}

case "$1" in
    push)
        sync_push
        ;;
    pull)
        sync_pull
        ;;
    *)
        echo "用法: bash memory_sync.sh [push|pull]"
        echo "  push - 推送本地记忆到 NAS"
        echo "  pull - 从 NAS 拉取最新记忆"
        ;;
esac
