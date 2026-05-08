#!/usr/bin/env python3
"""
read_wechat.py - 微信公众号文章读取器
使用搜狗微信搜索 + 直接访问混合方案

使用方法:
  python3 read_wechat.py <公众号文章URL>
  python3 read_wechat.py --search <关键词>   # 搜索文章
"""

import re
import sys
import json
import time
import html2text
import requests

h2t = html2text.HTML2Text()
h2t.body_width = 0
h2t.ignore_links = False

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://weixin.sogou.com/',
}


def extract_article_id(url: str) -> str:
    """从URL提取文章ID"""
    match = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else ""


def read_direct(url: str) -> dict:
    """直接访问 mp.weixin.qq.com"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        
        if '参数错误' in r.text or r.status_code != 200:
            return {"error": "文章不可访问（需微信授权）", "url": url}
        
        body = r.text
        
        # 检查是否真的有内容
        if 'id="js_content"' not in body:
            return {"error": "未找到正文区域", "url": url}
        
        # 提取标题
        title_match = re.search(r'id="activity-name"[^>]*>([^<]+)</h1>', body)
        title = title_match.group(1).strip() if title_match else "无标题"
        
        # 提取作者
        author_match = re.search(r'id="js_name"[^>]*>([^<]+)</span>', body)
        author = author_match.group(1).strip() if author_match else ""
        
        # 提取正文HTML
        content_match = re.search(r'id="js_content"[^>]*>(.*?)</div>', body, re.DOTALL)
        content_html = content_match.group(1) if content_match else ""
        content = re.sub(r'<[^>]+>', '', content_html)
        content = re.sub(r'\s+', ' ', content).strip()
        
        # 提取时间
        time_match = re.search(r'id="publish_time"[^>]*>([^<]+)</span>', body)
        pub_time = time_match.group(1).strip() if time_match else ""
        
        # 转换为Markdown
        content_md = h2t.handle(content_html).strip() if content_html else content
        
        return {
            "title": title,
            "author": author,
            "content": content,
            "content_md": content_md,
            "publish_time": pub_time,
            "platform": "wechat",
            "url": url,
        }
        
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "url": url}


def read_via_sogou(url_or_keyword: str = None, keyword: str = None) -> dict:
    """通过搜狗微信搜索读取文章"""
    try:
        s = requests.Session()
        s.headers.update(HEADERS)
        
        if keyword:
            # 搜索文章
            r = s.get('https://weixin.sogou.com/weixin',
                     params={'type': 'article', 'query': keyword, 'ie': 'utf8'},
                     timeout=15)
            
            if r.status_code != 200:
                return {"error": f"搜狗搜索失败: {r.status_code}"}
            
            # 提取文章链接
            links = re.findall(r'href="(https://mp\.weixin\.qq\.com/s/[^"]+)"', r.text)
            if not links:
                return {"error": "搜狗未找到相关文章", "keyword": keyword}
            
            article_url = links[0]
        else:
            article_url = url_or_keyword
        
        # 访问文章
        r = s.get(article_url, headers=HEADERS, timeout=15)
        
        if r.status_code != 200:
            return {"error": f"文章访问失败: {r.status_code}", "url": article_url}
        
        body = r.text
        
        # 检查是否需要授权
        if '参数错误' in body:
            # 尝试通过搜狗缓存访问
            return {"error": "需微信授权，尝试搜狗缓存...", "url": article_url}
        
        # 提取内容
        content_match = re.search(r'id="js_content"[^>]*>(.*?)</div>', body, re.DOTALL)
        content_html = content_match.group(1) if content_match else ""
        content = re.sub(r'<[^>]+>', '', content_html)
        content = re.sub(r'\s+', ' ', content).strip()
        
        title_match = re.search(r'id="activity-name"[^>]*>([^<]+)</h1>', body)
        author_match = re.search(r'id="js_name"[^>]*>([^<]+)</span>', body)
        
        return {
            "title": title_match.group(1).strip() if title_match else "",
            "author": author_match.group(1).strip() if author_match else "",
            "content": content,
            "content_md": h2t.handle(content_html).strip() if content_html else content,
            "platform": "wechat",
            "url": article_url,
            "source": "sogou" if keyword else "direct",
        }
        
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 read_wechat.py <文章URL>")
        print("  python3 read_wechat.py --search <关键词>")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == '--search' and len(sys.argv) >= 3:
        keyword = sys.argv[2]
        print(f"[搜索关键词] {keyword}")
        result = read_via_sogou(keyword=keyword)
    elif arg.startswith('http'):
        print(f"[直接访问] {arg}")
        # 优先直接访问
        result = read_direct(arg)
        if "error" in result:
            print(f"  直接访问失败: {result['error']}")
            print("  尝试搜狗...")
            result = read_via_sogou(url_or_keyword=arg)
    else:
        print(f"[搜索] {arg}")
        result = read_via_sogou(keyword=arg)
    
    if "error" in result:
        print(f"\n❌ 错误: {result['error']}")
        if result.get('url'):
            print(f"   URL: {result['url']}")
        sys.exit(1)
    
    print(f"\n📕 【微信公众号】{result.get('title', '无标题')}")
    if result.get('author'):
        print(f"👤 {result['author']}")
    if result.get('publish_time'):
        print(f"🕐 {result['publish_time']}")
    print(f"🔗 {result.get('url', '')}")
    print(f"\n📝 正文:\n{result.get('content', result.get('content_md', '(无正文)'))[:500]}")
    
    # 保存完整数据
    out = f"/tmp/wechat_article_{extract_article_id(result.get('url', 'unknown'))}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 完整数据: {out}")


if __name__ == "__main__":
    main()