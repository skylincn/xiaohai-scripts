#!/usr/bin/env python3
"""
Search Master - 小海虾深度搜索工具 v1.0
支持: Bing RSS / Jina Reader / 代理自动切换
用法: python3 search_master.py "搜索词" [--num N] [--url-only]
"""

import subprocess
import sys
import json
import re
import urllib.parse
import time
from typing import List, Dict, Optional

PROXY = "http://127.0.0.1:10808"

class SearchMaster:
    def __init__(self, proxy: str = PROXY):
        self.proxy = proxy
        
    def _curl(self, url: str, timeout: int = 15) -> Optional[str]:
        """通过代理发起 HTTP GET"""
        cmd = [
            "curl", "-s", "--max-time", str(timeout),
            "--proxy", self.proxy, url
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            return result.stdout if result.returncode == 0 else None
        except Exception:
            return None
    
    def search_bing(self, query: str, num: int = 5) -> List[Dict]:
        """Bing RSS 搜索，返回标题+URL列表"""
        encoded = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={encoded}&format=rss"
        
        xml = self._curl(url)
        if not xml:
            return []
        
        results = []
        # 解析 <title>...</title> 和 <link>...</link>
        titles = re.findall(r'<title>([^<]+)</title>', xml)
        links = re.findall(r'<link>([^<]+)</link>', xml)
        
        for i, title in enumerate(titles[1:num+1]):  # 跳过第一个（RSS标题）
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            if not clean_title or clean_title in ['Bing', '搜尋結果']:
                continue
            results.append({
                "title": clean_title,
                "url": links[i+1] if i+1 < len(links) else ""
            })
        return results
    
    def extract_content(self, url: str, max_chars: int = 500) -> str:
        """用 Jina AI Reader 提取页面正文"""
        jina_url = f"https://r.jina.ai/{urllib.parse.quote(url)}"
        content = self._curl(jina_url, timeout=20)
        if content:
            # 去掉 Jina 的元信息头
            lines = content.split('\n')
            content_lines = []
            skip_meta = True
            for line in lines:
                if skip_meta and line.startswith('---'):
                    skip_meta = False
                    continue
                if not skip_meta:
                    content_lines.append(line)
            text = '\n'.join(content_lines).strip()
            return text[:max_chars] + ("..." if len(text) > max_chars else "")
        return "(内容获取失败)"
    
    def deep_search(self, query: str, num: int = 5) -> Dict:
        """
        深度搜索：搜索 + 内容提取
        返回结构化结果
        """
        print(f"[SearchMaster] 🔍 搜索: {query}", file=sys.stderr)
        
        results = self.search_bing(query, num)
        if not results:
            return {"query": query, "results": [], "error": "Bing 搜索失败"}
        
        print(f"[SearchMaster] ✅ 找到 {len(results)} 条结果，开始提取内容...", file=sys.stderr)
        
        output = []
        for i, r in enumerate(results):
            print(f"[SearchMaster]   [{i+1}] {r['title'][:60]}...", file=sys.stderr)
            content = self.extract_content(r['url']) if r['url'] else ""
            output.append({
                "title": r['title'],
                "url": r['url'],
                "content": content
            })
        
        return {
            "query": query,
            "count": len(output),
            "results": output
        }
    
    def search_and_display(self, query: str, num: int = 5, url_only: bool = False):
        """搜索并以可读格式输出"""
        if url_only:
            results = self.search_bing(query, num)
            for i, r in enumerate(results):
                print(f"{i+1}. {r['title']}")
                print(f"   → {r['url']}")
            return
        
        data = self.deep_search(query, num)
        print(f"\n{'='*60}")
        print(f"📋 搜索结果: {data['query']} ({len(data.get('results', []))} 条)")
        print(f"{'='*60}")
        
        for i, r in enumerate(data.get('results', [])):
            print(f"\n📌 [{i+1}] {r['title']}")
            print(f"   🔗 {r['url']}")
            if r['content']:
                print(f"   📝 {r['content']}")
        
        print(f"\n{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Search Master - 小海虾搜索工具")
    parser.add_argument("query", help="搜索词")
    parser.add_argument("--num", "-n", type=int, default=5, help="结果数量")
    parser.add_argument("--url-only", "-u", action="store_true", help="只显示URL")
    parser.add_argument("--json", "-j", action="store_true", help="JSON格式输出")
    parser.add_argument("--proxy", "-p", default=PROXY, help="代理地址")
    
    args = parser.parse_args()
    
    searcher = SearchMaster(proxy=args.proxy)
    
    if args.json:
        result = searcher.deep_search(args.query, args.num)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        searcher.search_and_display(args.query, args.num, args.url_only)
