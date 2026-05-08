#!/bin/bash
# COS上传脚本
# 用法: ./cos_upload.sh <本地文件> <目标目录> [文件名]
source ~/.openclaw/workspace/.cos_env
FILE=$1
TARGET_DIR=${2:-"aioutput/"}
FNAME=${3:-$(basename "$1")}

export TENCENT_COS_SECRET_ID
export TENCENT_COS_SECRET_KEY
export TENCENT_COS_REGION

mcporter call cos-mcp.putObject filePath="$FILE" fileName="$FNAME" targetDir="$TARGET_DIR" 2>&1 | python3 -c "
import json,sys
d=json.load(sys.stdin)
if d.get('statusCode') == 200:
    key = d.get('Key','')
    bucket = d.get('Bucket','')
    region = '$TENCENT_COS_REGION'
    print(f'✅ 上传成功')
    print(f'📁 COS路径: {key}')
    print(f'🔗 公开链接: https://{bucket}.cos.{region}.myqcloud.com/{key}')
else:
    print(f'❌ 失败: {d}')
"
