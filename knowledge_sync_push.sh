#!/bin/bash
# 分类知识同步推送脚本
# 将小海虾的knowledge分类推送到NAS，供小河虾/小罗虾学习
#
# 知识分类：
#   knowledge/skills/    → 小海虾学到的技能/方法（三虾共享）
#   knowledge/mac/      → Mac使用技巧（小罗虾专长）
#   knowledge/nas/      → NAS使用经验（小河虾专长）
#   knowledge/prompts/  → 好的prompt模板（三虾共享）
#
# cron建议：每天1次（9AM）

NAS_HOST="152.136.61.172"
NAS_SSH_PORT="7422"
NAS_USER="skyyz"
NAS_PASS="Lin998007"

WORKSPACE_DIR="/root/.openclaw/workspace"
COORD_DIR="$WORKSPACE_DIR/coordination"
KNOWLEDGE_DIR="$COORD_DIR/knowledge"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [xiaohaixia] $*" >&2; }

get_nas_path() {
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
        'ls -d /volume2/homes/sk??z/shared/coordination 2>/dev/null || ls -d /var/services/homes/sk??z/shared/coordination 2>/dev/null' 2>/dev/null
}

# 推送知识文件到NAS
push_knowledge() {
    local nas_path=$(get_nas_path)
    if [ -z "$nas_path" ]; then
        error "无法连接NAS"
        return 1
    fi

    log "推送分类知识到NAS..."

    # 确保目录存在
    sshpass -p "$NAS_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 -p "$NAS_SSH_PORT" "$NAS_USER@$NAS_HOST" \
        "mkdir -p $nas_path/knowledge/skills $nas_path/knowledge/mac $nas_path/knowledge/nas $nas_path/knowledge/prompts" 2>/dev/null

    # 遍历knowledge目录，push每个文件
    for category in skills mac nas prompts; do
        local src_dir="$KNOWLEDGE_DIR/$category"
        if [ -d "$src_dir" ]; then
            for f in $(ls "$src_dir"/*.md 2>/dev/null); do
                if [ -f "$f" ]; then
                    local fname=$(basename "$f")
                    sshpass -p "$NAS_PASS" scp -o StrictHostKeyChecking=no \
                        -o ConnectTimeout=10 -P "$NAS_SSH_PORT" "$f" \
                        "$NAS_USER@$NAS_HOST:$nas_path/knowledge/$category/$fname" 2>/dev/null
                    log "  ✅ $category/$fname"
                fi
            done
        fi
    done

    log "推送完成！"
}

pull_and_merge() {
    log "拉取其他虾的知识..."
    # 小河虾和小罗虾的知识可以pull回来合并
}

case "${1:-push}" in
    push) push_knowledge ;;
    pull) pull_and_merge ;;
    *) echo "用法: $0 [push|pull]" ;;
esac
