#!/bin/bash
# 三虾记忆同步推送脚本 v5
# 改进：用 cat + 本地解析替代远程 Python，彻底解决 SSH quoting 问题
#
# 路径：/workspace/scripts/memory_sync_push.sh
# cron：9AM / 2PM / 9PM

NAS_HOST="152.136.61.172"
NAS_SSH_PORT="7422"
NAS_USER="skyyz"
NAS_PASS="Lin998007"

WORKSPACE_DIR="/root/.openclaw/workspace"
COORD_DIR="$WORKSPACE_DIR/coordination"
SHARED_JSON="$COORD_DIR/memory.json"

# 小河虾记忆目录（NAS 本地）
NAS_MEMORY_DIR="/var/services/homes/skyyz/.openclaw/workspace/memory"
NAS_OPENCLAIM_DIR="/var/services/homes/skyyz/.openclaw/workspace"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [xiaohaixia] $*" >&2; }
error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [xiaohaixia] ERROR: $*" >&2; }

get_nas_coord_path() {
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
        'ls -d /volume2/homes/sk??z/shared/coordination' 2>/dev/null | grep -v '^$' | tail -1 | tr -d '\r\n'
}

# 拉取小河虾记忆（用 cat + 本地 node 解析）
pull_xiaoheixia() {
    log "尝试拉取小河虾记忆..."
    
    local xhh_tmp="/tmp/xhh_$$.txt"
    
    # 用 SSH cat 拉取小河虾今天的记忆文件
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=15 -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
        "cat $NAS_MEMORY_DIR/2026-04-14.md $NAS_MEMORY_DIR/2026-04-13.md 2>/dev/null" > "$xhh_tmp" 2>/dev/null || true
    
    if [ -s "$xhh_tmp" ]; then
        local count=$(grep -v '^#' "$xhh_tmp" | grep -v '^---' | grep -v '^$' | wc -l)
        log "小河虾：拉取到 $count 行记忆"
        
        # 用本地 node 解析并合并
        node -e "
const fs = require('fs');
const content = fs.readFileSync('$xhh_tmp', 'utf8');
const lines = content.split('\n');
const textLines = lines.filter(l => l.trim() && !l.trim().startsWith('#') && !l.trim().startsWith('---') && !l.trim().startsWith('**') && !l.trim().startsWith('\`'));
const entry = {
    type: 'daily',
    source: '2026-04-14.md',
    content: textLines.join('\n').substring(0, 2000),
    synced_at: new Date().toISOString(),
    shrimp: 'xiaoheixia'
};
console.log(JSON.stringify(entry));
" 2>/dev/null
    else
        log "小河虾：今日无记忆（正常，小河虾可能未更新）"
    fi
    
    rm -f "$xhh_tmp"
}

# 拉取小罗虾的记忆（通过 HTTP API）
pull_xiaoluo() {
    log "尝试拉取小罗虾记忆..."
    
    for port in 18790 18791; do
        local xl_tmp="/tmp/xl_$$.json"
        curl -s --max-time 5 "http://localhost:$port/api/memory" > "$xl_tmp" 2>/dev/null
        if [ -s "$xl_tmp" ]; then
            local count=$(node -e "const d=require('$xl_tmp'); console.log(d.entries?d.entries.length:0)" 2>/dev/null || echo 0)
            if [ "$count" -gt 0 ]; then
                log "小罗虾：通过 localhost:$port 拉取到 $count 条记忆"
                cat "$xl_tmp"
                rm -f "$xl_tmp"
                return
            fi
        fi
        rm -f "$xl_tmp"
    done
    
    log "小罗虾：不在线（Mac 非全天候开机，正常）"
    echo '{"shrimp":"xiaoluo","entries":[]}'
}

merge_and_sync() {
    log "=== 记忆同步开始 ==="
    
    # 拉取小河虾
    local xhh_entry=$(pull_xiaoheixia)
    local xl_json=$(pull_xiaoluo)
    
    # 写临时文件
    local xhh_tmp="/tmp/xhh_entry_$$.json"
    local xl_tmp="/tmp/xl_mem_$$.json"
    echo "$xl_json" > "$xl_tmp"
    
    # 读取小海虾本地 memory.json 作为基础
    node -e "
const fs = require('fs');

const SHARED_FILE = '$SHARED_JSON';
const XHH_ENTRY = $xhh_entry || null;
const XL_FILE = '$xl_tmp';
const now = new Date().toISOString();

// 读取现有 shared
let shared = { version:'1.0', entries:[] };
if (fs.existsSync(SHARED_FILE)) {
    try { shared = JSON.parse(fs.readFileSync(SHARED_FILE, 'utf8')); } catch(e) {}
}

// 过滤掉xiaohaixia的旧条目
let otherEntries = (shared.entries||[]).filter(e => e.shrimp !== 'xiaohaixia');

// 添加小河虾的新条目（如果有）
if (XHH_ENTRY) otherEntries.push(XHH_ENTRY);

// 添加小罗虾的条目
try {
    const xlData = JSON.parse(fs.readFileSync(XL_FILE, 'utf8'));
    if (xlData.entries && xlData.entries.length > 0) {
        const xlEntries = xlData.entries.map(e => ({...e, shrimp:'xiaoluo', synced_at: now}));
        otherEntries.push(...xlEntries);
    }
} catch(e) {}

// 读取小海虾本地 memory 目录
const MEM_DIR = '/root/.openclaw/workspace/memory';
let xiaohaixiaEntries = [];
try {
    const files = fs.readdirSync(MEM_DIR).filter(f => /^\d{4}-\d{2}-\d{2}\.md$/.test(f)).sort().slice(-7);
    for (const f of files) {
        const fp = MEM_DIR + '/' + f;
        const c = fs.readFileSync(fp, 'utf8');
        const lines = c.split('\n').filter(l => l.trim() && !l.startsWith('#') && !l.startsWith('---'));
        if (lines.length) xiaohaixiaEntries.push({type:'daily', source:f, content:lines.join('\n').substring(0,2000), shrimp:'xiaohaixia', synced_at:now, local_mtime:fs.statSync(fp).mtime.toISOString()});
    }
    const mf = '/root/.openclaw/workspace/MEMORY.md';
    if (fs.existsSync(mf)) {
        const c = fs.readFileSync(mf, 'utf8');
        const secs = c.split(/(?=^## )/m).slice(-3);
        if (secs.length) xiaohaixiaEntries.push({type:'memory', source:'MEMORY.md', content:secs.join('\n').substring(0,1500), shrimp:'xiaohaixia', synced_at:now});
    }
} catch(e) {}

// 合并
shared.entries = [...otherEntries, ...xiaohaixiaEntries];
shared.last_sync = now;
shared.last_sync_by = 'xiaohaixia';

fs.writeFileSync(SHARED_FILE, JSON.stringify(shared, null, 2));

const counts = {};
shared.entries.forEach(e => { counts[e.shrimp] = (counts[e.shrimp]||0)+1; });
console.error('合并完成：' + JSON.stringify(counts) + ' 总'+shared.entries.length+'条');
" 2>&1
    
    rm -f "$xhh_tmp" "$xl_tmp"
    
    # 推送 NAS
    local NAS_COORD_PATH=$(get_nas_coord_path)
    if [ -z "$NAS_COORD_PATH" ]; then
        error "NAS 不在线，跳过推送"
        return 1
    fi
    
    cat "$SHARED_JSON" | \
        sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
            "cat > '$NAS_COORD_PATH/memory.json'" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        local count=$(sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
            "python3 -c \"import json; print(len(json.load(open('$NAS_COORD_PATH/memory.json'))['entries']))\"")
        log "推送成功！NAS 上共 $count 条记忆"
    else
        error "推送失败"
    fi
}

merge_and_sync
