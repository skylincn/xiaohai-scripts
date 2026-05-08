#!/usr/bin/env python3
"""
read_wechat_article.py - 微信公众号文章读取器
使用搜狗微信搜索获取文章列表和内容

无需登录，无需 Cookie，直接抓取
"""

import sys, re, html, json
from urllib.parse import quote

def search_wechat_articles(keyword: str, max_results: int = 5) -> dict:
    """
    搜索微信公众号文章
    Args:
        keyword: 搜索关键词
        max_results: 返回最多几条
    Returns:
        {"articles": [{"title", "url", "source", "digest", "date"}, ...], "total": int}
    """
    # 搜狗微信搜索
    url = f"https://weixin.sogou.com/weixin?type=2&query={quote(keyword)}&ie=utf8"
    
    import urllib.request
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode('utf-8', errors='replace')
    
    # 清理 HTML
    text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 从完整 HTML 提取文章链接
    article_urls = re.findall(r'(https?://mp\.weixin\.qq\.com/s/[a-zA-Z0-9_-]+)', content)
    article_urls = list(dict.fromkeys(article_urls))[:max_results]  # 去重并限制数量
    
    # 从纯文本提取标题和摘要
    # 找 keyword 附近的上下文
    results = []
    lower_text = text.lower()
    keyword_lower = keyword.lower()
    
    idx = lower_text.find(keyword_lower)
    while idx > 0 and len(results) < max_results:
        start = max(0, idx - 200)
        end = min(len(text), idx + 400)
        snippet = text[start:end].strip()
        
        # 提取标题（通常在关键词前100字内）
        title_match = re.search(r'([^\s]{5,50}?)(?=[:：\s](?:openclaw|小红书|openaiclaw|aicg|ai|chatgpt|自动化))', snippet, re.IGNORECASE)
        
        # 尝试提取来源
        source_match = re.search(r'来源[:：]\s*([^\s，,]{2,20})', snippet)
        date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)', snippet)
        
        # 提取摘要
        digest_match = re.search(r'([^\n。]{20,80}。)[:：]', snippet)
        
        article_info = {
            "title": title_match.group(1).strip() if title_match else f"文章{len(results)+1}",
            "url": article_urls[len(results)] if len(results) < len(article_urls) else "",
            "source": source_match.group(1).strip() if source_match else "微信公众号",
            "date": date_match.group(1).strip() if date_match else "",
            "digest": digest_match.group(1).strip() if digest_match else snippet[:100],
            "keyword": keyword
        }
        
        if article_info["url"]:
            results.append(article_info)
        
        idx = lower_text.find(keyword_lower, idx + 1)
    
    return {"articles": results, "total": len(results)}


def read_article(url: str) -> dict:
    """
    读取单篇文章内容（部分文章可直接读取，部分需要授权）
    """
    import urllib.request
    
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        
        # 提取 og:title
        og_title = re.search(r'property="og:title"[^>]*content="([^"]+)"', content)
        og_desc = re.search(r'property="og:description"[^>]*content="([^"]+)"', content)
        og_author = re.search(r'class="rich_media_meta rich_media_meta_nickname[^>]*>([^<]+)<', content)
        date_match = re.search(r'publish_time.*?(\d{4}-\d{2}-\d{2})', content)
        
        # 提取正文（section 标签内的纯文本）
        sections = re.findall(r'<section[^>]*>(.*?)</section>', content, re.DOTALL)
        texts = []
        for s in sections:
            clean = re.sub(r'<[^>]+>', '', s).strip()
            if len(clean) > 15:
                texts.append(clean)
        
        result = {
            "title": og_title.group(1) if og_title else "未知标题",
            "author": og_author.group(1).strip() if og_author else "未知作者",
            "date": date_match.group(1) if date_match else "",
            "description": og_desc.group(1) if og_desc else "",
            "url": url,
            "content": "\n".join(texts[:50]),  # 限制50段
            "readable": True
        }
        
        # 检查是否需要授权
        if "请在微信中打开" in content or "参数错误" in content:
            result["readable"] = False
            result["error"] = "需要微信授权"
        
        return result
        
    except Exception as e:
        return {"error": str(e), "readable": False}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  搜索: python3 read_wechat_article.py 搜索 <关键词>")
        print("  读取: python3 read_wechat_article.py 读取 <URL>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "搜索":
        keyword = sys.argv[2] if len(sys.argv) > 2 else "openclaw 小红书"
        results = search_wechat_articles(keyword, max_results=5)
        print(f"\n📢 微信公众号搜索「{keyword}」，共找到 {results['total']} 条")
        print("=" * 60)
        for i, art in enumerate(results['articles'], 1):
            print(f"\n【{i}】{art['title']}")
            print(f"   来源: {art['source']} | 日期: {art['date']}")
            print(f"   摘要: {art['digest'][:80]}...")
            if art['url']:
                print(f"   链接: {art['url']}")
        print()
    
    elif cmd == "读取":
        url = sys.argv[2] if len(sys.argv) > 2 else ""
        if not url:
            print("请提供文章URL")
            sys.exit(1)
        result = read_article(url)
        if result.get("readable"):
            print(f"\n📰 {result['title']}")
            print(f"👤 {result['author']} | 📅 {result['date']}")
            print("-" * 60)
            print(result['content'][:2000])
        else:
            print(f"❌ {result.get('error', '读取失败')}")