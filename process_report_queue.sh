#!/bin/bash
# 报告队列处理器 - 小海虾每5分钟轮询 NAS 队列，转发飞书，有问题则标记
# 被调用方式：cron 每5分钟触发一次

TARGET=$(sshpass -p 'Lin998007' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p 7422 skyyz@152.136.61.172 'ls -d /volume2/homes/sk??z/shared/coordination' 2>/dev/null)
QUEUE="$TARGET/report_queue.json"
LOCK="$QUEUE.processing"

# 避免并发
[ -f "$LOCK" ] && exit 0
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# 读取队列（空则退出）
CONTENT=$(sshpass -p 'Lin998007' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p 7422 skyyz@152.136.61.172 "cat '$QUEUE'" 2>/dev/null)
[ -z "$CONTENT" ] && exit 0

# 解析 JSON，提取未发送的项目
echo "$CONTENT" | python3 -c "
import sys, json

try:
    queue = json.load(sys.stdin)
except:
    print('[]')
    sys.exit(0)

pending = [item for item in queue if not item.get('sent', False)]
print(json.dumps(pending))
" > /tmp/pending_reports.json 2>/dev/null

PENDING=$(cat /tmp/pending_reports.json)
[ "$PENDING" = "[]" ] && exit 0

# 对于每个待处理报告，输出摘要供 cron agent 分析并发送飞书
echo "$PENDING" | python3 -c "
import sys, json
items = json.load(sys.stdin)
for item in items:
    print('---REPORT---')
    print('FROM:', item.get('shrimp', '?'))
    print('TYPE:', item.get('type', '?'))
    print('TIME:', item.get('timestamp', '?'))
    print('CONTENT:', item.get('content', '')[:300])
" > /tmp/pending_reports.txt 2>/dev/null

cat /tmp/pending_reports.txt

# 标记为已处理（cron agent 发送成功后才会真正清空）
# 这里只输出，发送由 cron agent 接管
