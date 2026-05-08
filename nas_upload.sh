#!/bin/bash
# NAS共享盘上传脚本 - 通过SSH(FRP)上传文件到NAS共享目录
# 用法: ./nas_upload.sh <本地文件> <目标目录> [远程文件名]
# 示例: ./nas_upload.sh /tmp/test.png IMG
#       ./nas_upload.sh /tmp/report.pdf IMG report.pdf

NAS_HOST="152.136.61.172"
NAS_PORT="7422"
NAS_USER="skyyz"
NAS_PASS="Lin998007"
# 共享盘实际路径: /volume1/claw/
REMOTE_BASE="/volume1/claw"

FILE="$1"
DEST_DIR="$2"
DEST_NAME="${3:-$(basename "$FILE")}"

if [ -z "$FILE" ] || [ -z "$DEST_DIR" ]; then
    echo "用法: $0 <本地文件> <目标目录> [远程文件名]"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "文件不存在: $FILE"
    exit 1
fi

REMOTE_PATH="${REMOTE_BASE}/${DEST_DIR}/${DEST_NAME}"

cat "$FILE" | sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p "$NAS_PORT" \
    "$NAS_USER@$NAS_HOST" "cat > '$REMOTE_PATH'" 2>&1
EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo "✅ 上传成功: $DEST_NAME → NAS $DEST_DIR/"
else
    echo "❌ 上传失败 (exit $EXIT)"
fi

exit $EXIT
