#!/bin/bash
# System Healer - 自动修复常见问题
# 由 KAIROS 巡查触发，检测到问题时自动修复

LOG_TAG="[healer]"
REPAIR_LOG="/root/.openclaw/workspace/memory/healer_log.jsonl"
WORKSPACE="/root/.openclaw/workspace"

log_repair() {
  local action="$1" status="$2" detail="$3"
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"action\":\"$action\",\"status\":\"$status\",\"detail\":\"$detail\"}" >> "$REPAIR_LOG"
  echo "$LOG_TAG $action: $status - $detail"
}

heal_disk() {
  local usage=$(df / | awk 'NR==2{print $5}' | tr -d %)
  if [ "$usage" -gt 80 ]; then
    echo "$LOG_TAG 磁盘使用率 ${usage}% > 80%，开始清理..."
    
    # 1. npm cache
    local npm_cache=$(du -sm /home/ubuntu/.npm 2>/dev/null | awk '{print $1}' || echo 0)
    if [ "$npm_cache" -gt 50 ]; then
      npm cache clean --force 2>/dev/null
      log_repair "npm_cache_clean" "done" "清理 ${npm_cache}MB"
    fi
    
    # 2. docker 占用
    if command -v docker &>/dev/null; then
      local docker_space=$(docker system df 2>/dev/null | grep "Build cache" | awk '{print $4}' | tr -d GB | awk '{printf "%d", $1*1024}' || echo 0)
      if [ "$docker_space" -gt 100 ]; then
        docker builder prune -af 2>/dev/null
        docker image prune -af --filter "until=168h" 2>/dev/null
        log_repair "docker_prune" "done" "清理 Docker build cache"
      fi
    fi
    
    # 3. 旧日志文件 (>7天, >10MB)
    find /root/.openclaw/workspace/skills/evolver/memory -name "*.jsonl" -size +10M -mtime +7 -exec gzip {} \; 2>/dev/null
    log_repair "log_compress" "done" "压缩大日志文件"
    
    # 4. journal logs
    journalctl --vacuum-size=100M 2>/dev/null
    
    local new_usage=$(df / | awk 'NR==2{print $5}' | tr -d %\ )
    echo "$LOG_TAG 清理完成: ${usage}% → ${new_usage}%"
    log_repair "disk_heal" "done" "${usage}% -> ${new_usage}%"
  else
    echo "$LOG_TAG 磁盘 ${usage}% 正常"
  fi
}

heal_gateway() {
  # 检查 Gateway 是否在运行
  if ! pgrep -f "openclaw" > /dev/null; then
    echo "$LOG_TAG Gateway 未运行，尝试重启..."
    export NVM_DIR="/home/ubuntu/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    
    cd /root/.openclaw && npx openclaw gateway start 2>&1 &
    sleep 5
    
    if pgrep -f "openclaw" > /dev/null; then
      log_repair "gateway_restart" "success" "Gateway 已恢复"
    else
      log_repair "gateway_restart" "failed" "Gateway 重启失败"
    fi
  else
    echo "$LOG_TAG Gateway 运行正常"
  fi
}

heal_zombie() {
  local zombies=$(ps aux | awk '$8=="Z" {print $2}' | wc -l)
  if [ "$zombies" -gt 5 ]; then
    echo "$LOG_TAG 发现 $zombies 个僵尸进程，尝试清理..."
    # 杀掉父进程来回收僵尸
    ps aux | awk '$8=="Z" {print $3}' | sort -u | while read ppid; do
      [ "$ppid" != "1" ] && kill -9 "$ppid" 2>/dev/null
    done
    log_repair "zombie_clean" "done" "清理 $zombies 僵尸进程"
  fi
}

heal_memory() {
  local mem_pct=$(free | awk 'NR==2{printf "%.0f", $3/$2*100}')
  if [ "$mem_pct" -gt 90 ]; then
    echo "$LOG_TAG 内存 ${mem_pct}% > 90%，释放缓存..."
    sync && echo 3 > /proc/sys/vm/drop_caches
    local new_mem=$(free | awk 'NR==2{printf "%.0f", $3/$2*100}')
    log_repair "memory_release" "done" "${mem_pct}% -> ${new_mem}%"
  fi
}

# === 主流程 ===
echo "=== System Healer $(date -u) ==="
heal_disk
heal_gateway
heal_zombie
heal_memory
echo "=== Healer Complete ==="
