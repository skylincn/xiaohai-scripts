#!/bin/bash
# 🦐 会话启动加载脚本 - 自动同步跨平台记忆

echo "=== 🦐 小海虾记忆同步 ==="

# 1. 拉取 NAS 最新记忆
bash /root/.openclaw/workspace/scripts/memory_sync.sh pull 2>/dev/null || echo "NAS 同步跳过（可能离线）"

# 2. 显示今日上下文
TODAY=$(date +%Y-%m-%d)
echo ""
echo "=== 今日记忆 ($TODAY) ==="
if [ -f "/root/.openclaw/workspace/memory/$TODAY.md" ]; then
    echo "✅ 今日记忆存在 ($(wc -l < /root/.openclaw/workspace/memory/$TODAY.md) 行)"
else
    echo "📝 今日记忆未创建"
fi

# 3. 显示跨平台状态
echo ""
echo "=== 跨平台状态 ==="
if [ -f /tmp/session_context.json ]; then
    python3 -c "
import json
with open('/tmp/session_context.json') as f:
    d = json.load(f)
    print(f\"最后更新: {d.get('lastUpdate', 'N/A')}\")
    print(f\"来源平台: {d.get('platform', 'N/A')}\")
" 2>/dev/null || echo "无跨平台上下文"
fi

echo ""
echo "✅ 记忆同步完成，开始服务老大！"
