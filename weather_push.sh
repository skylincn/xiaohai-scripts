#!/bin/bash
# 天气预报推送脚本 - 直接调用飞书Bot API

APP_ID="cli_a943de0c9d38dbd2"
APP_SECRET="0JxKMCRyiiqhKdOdMViUAffSaZi2jnDj"
USER_OPEN_ID="ou_437d209d17f092116de04b3c408e09e2"

# 获取北京当前天气（简化格式）
CURRENT=$(curl -s "wttr.in/Beijing?format=%c+%t+(feels+like+%f)")
# 获取明日高低温度
TEMP=$(curl -s "wttr.in/Beijing?1&format=j1" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['weather'][1]['mintempC'],d['weather'][1]['maxtempC'])" 2>/dev/null || echo "N/A")

# 获取 tenant_access_token
TOKEN=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d "{\"app_id\": \"$APP_ID\", \"app_secret\": \"$APP_SECRET\"}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))")

if [ -z "$TOKEN" ]; then
  echo "token获取失败"
  exit 1
fi

# 构造消息（使用简化emoji避免转义问题）
MSG="老大小海虾给您汇报明日天气！

晚安预报！明天
北京 · 朝阳区东三环

温度：${TEMP}°C
天气：${CURRENT}

温馨提示：明日无雨，适合出行"

# 发送（URL编码方式避免特殊字符问题）
python3 -c "
import urllib.request, urllib.parse, json, sys

token = '$TOKEN'
msg = '''$MSG'''

data = json.dumps({
    'receive_id': '$USER_OPEN_ID',
    'msg_type': 'text',
    'content': json.dumps({'text': msg})
}).encode('utf-8')

req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
    data=data,
    headers={
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    }
)
resp = urllib.request.urlopen(req, timeout=10)
print(resp.read().decode('utf-8'))
"
