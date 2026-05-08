#!/bin/bash
# 知识库 RAG 同步脚本
# 每天定时把知识库最新内容同步到小屿的记忆

VAULT="/var/services/homes/skyyz/shared/llm-wiki"
MEMORY="/root/.openclaw/workspace-main/MEMORY.md"
TEMP="/tmp/vault_sync_temp.md"

echo "" >> $MEMORY
echo "---" >> $MEMORY
echo "## 知识库同步 $(date '+%Y-%m-%d %H:%M')" >> $MEMORY
echo "" >> $MEMORY

# 搜索最近修改的文件中的关键概念
cd "$VAULT" || exit 1

# 找出最近3天修改的概念页面
find . -name "*.md" -mtime -3 | grep concepts | while read f; do
    title=$(basename "$f" .md)
    echo "### $title" >> $TEMP
    head -20 "$f" | grep -E "^#|created|source" | head -5 >> $TEMP
    echo "" >> $TEMP
done

# 搜索特定关键词相关的内容
KEYWORDS=("AI" "工具" "知识" "第二大脑" "OpenClaw")
for kw in "${KEYWORDS[@]}"; do
    files=$(grep -rl "$kw" . 2>/dev/null | grep -v "^./.obsidian" | head -3)
    if [ -n "$files" ]; then
        echo "### 关键词: $kw" >> $TEMP
        for f in $files; do
            echo "- $(basename "$f")" >> $TEMP
        done
        echo "" >> $TEMP
    fi
done

cat $TEMP >> $MEMORY
rm $TEMP
echo "知识库同步完成" $(date)
