#!/bin/bash
# 搜索 Obsidian Vault
# 用法: bash vault_search.sh "关键词"

VAULT="/var/services/homes/skyyz/shared/llm-wiki"
QUERY="$1"
MAX=${2:-5}

if [ -z "$QUERY" ]; then
    echo "用法: $0 \"关键词\" [最大结果数]"
    exit 1
fi

# 搜索 Markdown 文件
RESULTS=$(grep -rl "$QUERY" "$VAULT" 2>/dev/null | head -$MAX)

if [ -z "$RESULTS" ]; then
    echo "未找到相关结果"
    exit 0
fi

echo "找到 $(echo "$RESULTS" | wc -l) 个相关文件："
echo ""

for file in $RESULTS; do
    rel_path="${file#$VAULT/}"
    echo "📄 $rel_path"
    # 显示匹配行上下文
    grep -B1 -A1 "$QUERY" "$file" 2>/dev/null | head -6
    echo "---"
done
