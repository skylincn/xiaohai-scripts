#!/bin/bash
# NAS图片每日备份到COS脚本（修复版）
# 备份昨天新增的图片文件：NAS → 云服务器 → COS

TODAY=$(date +%Y%m%d)
YESTERDAY=$(date -d "yesterday" +%Y%m%d)
LOG_FILE="/root/.openclaw/workspace/logs/cos_backup.log"

source ~/.openclaw/workspace/.cos_env
export TENCENT_COS_SECRET_ID
export TENCENT_COS_SECRET_KEY
export TENCENT_COS_REGION

echo "[$TODAY] === COS备份开始: 昨天($YESTERDAY)的文件 ===" >> $LOG_FILE

NAS_HOST="152.136.61.172"
NAS_PORT="7422"
NAS_USER="skyyz"
NAS_PASS="Lin998007"
REMOTE_BASE="/volume1/claw"
# 旧路径已废弃：/var/services/homes/skyyz/shared

# 通过SSH(FRP)列出NAS昨天修改的图片文件
sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p "$NAS_PORT" \
  "$NAS_USER@$NAS_HOST" \
  "find ${REMOTE_BASE}/IMG/ -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.gif' -o -name '*.webp' \) -mtime 1" 2>/dev/null | \
  while read filepath; do
    fname=$(basename "$filepath")
    local_tmp="/tmp/cos_backup_${$}_${fname}"

    # SSH cat方式下载（避免SCP问题）
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -p "$NAS_PORT" \
      "$NAS_USER@$NAS_HOST" "cat '$filepath'" > "$local_tmp" 2>/dev/null

    if [ -s "$local_tmp" ]; then
      # 上传到COS
      result=$(python3 -c "
import os
from qcloud_cos import CosConfig, CosS3Client
secret_id = os.environ.get('TENCENT_COS_SECRET_ID')
secret_key = os.environ.get('TENCENT_COS_SECRET_KEY')
region = os.environ.get('TENCENT_COS_REGION', 'ap-beijing')
bucket = os.environ.get('TENCENT_COS_BUCKET', 'movie-1252813585')
config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
client = CosS3Client(config)
key = 'IMG/$fname'
try:
    with open('$local_tmp', 'rb') as f:
        r = client.put_object(Bucket=bucket, Body=f, Key=key)
    etag = r.get('ETag')
    print('OK' if etag else 'FAIL')
except Exception as e:
    print('ERR:' + str(e))
" 2>&1)
      rm -f "$local_tmp"
      if [ "$result" = "OK" ]; then
        echo "✅ $fname → COS" >> $LOG_FILE
      else
        echo "❌ $fname: $result" >> $LOG_FILE
      fi
    else
      echo "❌ $fname: SSH download failed" >> $LOG_FILE
      rm -f "$local_tmp"
    fi
  done

echo "[$TODAY] === COS备份完成 ===" >> $LOG_FILE
echo "备份完成，详情: $LOG_FILE"
