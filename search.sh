#!/bin/bash
# Search Master - 小海虾主力搜索脚本 v1.0
# 通过代理集群搜索，支持 Bing RSS + Jina AI Reader
# 用法: bash search.sh "搜索词" [数量] [--url-only]
#
# 依赖: curl, python3 (处理JSON/HTML)
# 代理: http://127.0.0.1:10808 (sing-box)

PROXY="http://127.0.0.1:10808"
MAX_RESULTS=${2:-5}
URL_ONLY=0

[[ "$3" == "--url-only" ]] && URL_ONLY=1

query="$1"
if [[ -z "$query" ]]; then
    echo "用法: $0 \"搜索词\" [数量] [--url-only]"
    exit 1
fi

# URL encode
encoded_query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")

echo "[Search Master] 搜索: $query (最多 $MAX_RESULTS 条结果)"
echo "---"

# Step 1: Bing RSS 搜索
bing_url="https://www.bing.com/search?q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")&format=rss"
search_results=$(curl -s --max-time 15 --proxy "$PROXY" "$bing_url" 2>/dev/null)

if [[ -z "$search_results" ]]; then
    echo "搜索失败: Bing 无响应"
    exit 1
fi

# 解析 RSS 结果
echo "$search_results" | grep -o '<title>[^<]*</title>' | tail -n +2 | head -n $MAX_RESULTS | while read -r title; do
    title=$(echo "$title" | sed 's/<[^>]*>//g')
    echo "$title"
done

if [[ $URL_ONLY -eq 1 ]]; then
    exit 0
fi

echo ""
echo "---"
echo "[内容提取] 使用 Jina AI Reader..."

# 提取 URL 并获取内容
count=0
echo "$search_results" | grep -oP 'https?://[^&"<>]+' | head -n $MAX_RESULTS | while read -r url; do
    # 跳过无效 URL
    [[ "$url" == *"microsoft.com"* ]] && continue
    [[ "$url" == *"bing.com"* ]] && continue
    [[ ${#url} -lt 20 ]] && continue
    
    ((count++))
    echo -e "\n[$count] $url"
    
    # 用 Jina 提取内容
    content=$(curl -s --max-time 15 --proxy "$PROXY" \
        -H "Accept: text/plain" \
        "https://r.jina.ai/$url" 2>/dev/null)
    
    if [[ -n "$content" ]]; then
        # 取前 300 字符
        echo "$content" | head -c 300
        echo "..."
    else
        echo "(内容获取失败)"
    fi
done

echo ""
echo "---"
echo "[Search Master] 完成"
