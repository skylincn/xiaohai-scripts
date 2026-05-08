#!/bin/bash
# 图片检查触发器
# 每5分钟由cron调用，发现新图片则唤醒主agent处理

INBOUND_DIR="/root/.openclaw/media/inbound"
QUEUE_FILE="/root/.openclaw/workspace/image-analysis/.queue.json"
OUTPUT_DIR="/root/.openclaw/workspace/image-analysis"

mkdir -p "$OUTPUT_DIR"

# 找所有图片，按修改时间排序，取最新的
latest_file=""
latest_mtime=0

for f in "$INBOUND_DIR"/*.png "$INBOUND_DIR"/*.jpg "$INBOUND_DIR"/*.jpeg "$INBOUND_DIR"/*.gif "$INBOUND_DIR"/*.webp "$INBOUND_DIR"/*.bmp; do
    [ -e "$f" ] || continue
    if [ -f "$f" ]; then
        size=$(stat -c%s "$f" 2>/dev/null || echo 0)
        if [ "$size" -gt 5000 ]; then
            mtime=$(stat -c%Y "$f" 2>/dev/null || echo 0)
            if [ "$mtime" -gt "$latest_mtime" ]; then
                latest_mtime=$mtime
                latest_file="$f"
            fi
        fi
    fi
done

if [ -n "$latest_file" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 发现新图片: $latest_file" >> /root/.openclaw/workspace/image-analysis/watcher.log
    # 创建触发文件，告知主agent有新图片待处理
    echo "$latest_file" > "$OUTPUT_DIR/.latest_image"
    echo "$(date +%s)" > "$OUTPUT_DIR/.last_check"
fi
