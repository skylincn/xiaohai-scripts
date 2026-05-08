#!/usr/bin/env python3
"""
搜索工具 v3.0 - 修复版
修复：代理可选、XML用标准库、支持多搜索源降级
"""

import subprocess
import urllib.parse
import re
import json
import time
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

class SearchMaster:
    def __init__(self, proxy: str = "auto"):
        """
        proxy: 代理设置
          - "auto": 自动检测（有代理用代理，没有直连）
          - "none": 强制直连（不使用代理）
          - 具体URL: 使用指定代理，如 "http://127.0.0.1:10808"
        """
        self.proxy = self._detect_proxy(proxy)
        self.last_source = None

    def _detect_proxy(self, proxy_setting: str) -> Optional[str]:
        """检测可用代理"""
        if proxy_setting.lower() == "none":
            return None
        if proxy_setting.lower() == "auto":
            # 尝试常见代理端口
            common_proxies = [
                "http://127.0.0.1:10808",  # sing-box
                "http://127.0.0.1:7890",     # Clash
                "http://127.0.0.1:1080",    # 通用
            ]
            for p in common_proxies:
                try:
                    result = subprocess.run(
                        ["curl", "-s", "--proxy", p, "--max-time", "3",
                         "https://www.google.com", "-o", "/dev/null", "-w", "%{http_code}"],
                        capture_output=True, timeout=5
                    )
                    if result.returncode == 0:
                        return p
                except:
                    pass
            return None  # 没找到可用代理，直连
        return proxy_setting

    def _curl(self, url: str, timeout: int = 15) -> Optional[str]:
        """执行 curl 请求"""
        cmd = ["curl", "-s", "--max-time", str(timeout), "-L"]
        
        if self.proxy:
            cmd += ["--proxy", self.proxy]
        
        cmd.append(url)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

    def _retry_curl(self, url: str, retries: int = 2, timeout: int = 15) -> Optional[str]:
        """带重试的 curl 请求"""
        for attempt in range(retries + 1):
            result = self._curl(url, timeout)
            if result:
                return result
            if attempt < retries:
                time.sleep(1)  # 等待后重试
        return None

    def _parse_bing_xml(self, xml_content: str, num: int = 5) -> List[Dict]:
        """解析 Bing RSS XML"""
        try:
            root = ET.fromstring(xml_content)
            items = root.findall('.//item')
            results = []
            for item in items[:num]:
                title = item.findtext('title', '').strip()
                link = item.findtext('link', '')
                desc = item.findtext('description', '').strip()
                # 过滤空标题和导航项
                if title and title not in ('Bing', '搜尋結果', 'Search Results'):
                    results.append({
                        "title": title,
                        "url": link,
                        "description": desc[:100] if desc else ''
                    })
            return results
        except ET.ParseError as e:
            # XML 解析失败，尝试正则降级
            return self._parse_bing_regex(xml_content, num)

    def _parse_bing_regex(self, content: str, num: int = 5) -> List[Dict]:
        """正则降级解析（仅在 XML 解析失败时使用）"""
        pattern = r'<item>\s*<title><!\[CDATA\[([^\]]+)\]\]></title>\s*<link>([^<]+)</link>'
        matches = re.findall(pattern, content, re.DOTALL)
        results = []
        for title, link in matches[:num]:
            if title.strip() and title.strip() not in ('Bing', '搜尋結果', 'Search Results'):
                results.append({"title": title.strip(), "url": link.strip(), "description": ''})
        return results

    def search_bing(self, query: str, num: int = 5) -> List[Dict]:
        """Bing RSS 搜索"""
        query_encoded = urllib.parse.quote(query)
        url = f"https://www.bing.com/search?q={query_encoded}&format=rss"
        
        content = self._retry_curl(url)
        if not content:
            return []
        
        results = self._parse_bing_xml(content, num)
        self.last_source = "bing"
        return results

    def search_jina(self, query: str, num: int = 5) -> List[Dict]:
        """Jina Reader 搜索（带降级）"""
        query_encoded = urllib.parse.quote(query)
        url = f"https://s.jina.ai/{query_encoded}"
        
        content = self._retry_curl(url, retries=2)
        if not content:
            return self.search_bing(query, num)  # 降级到 Bing
        
        try:
            data = json.loads(content)
            if data.get('code') == 200 and data.get('data'):
                results = []
                for item in data['data'][:num]:
                    results.append({
                        "title": item.get('title', ''),
                        "url": item.get('url', ''),
                        "description": item.get('content', '')[:100]
                    })
                self.last_source = "jina"
                return results
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Jina 解析失败，降级
        return self.search_bing(query, num)

    def search_ddg(self, query: str, num: int = 5) -> List[Dict]:
        """DuckDuckGo HTML 搜索（备用降级源）"""
        query_encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={query_encoded}"
        
        content = self._retry_curl(url)
        if not content:
            return []
        
        # 解析 DuckDuckGo HTML 结果
        pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, content)
        results = []
        seen_titles = set()
        for url, title in matches:
            title = re.sub(r'<[^>]+>', '', title).strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                results.append({"title": title, "url": url, "description": ''})
                if len(results) >= num:
                    break
        
        self.last_source = "ddg"
        return results

    def deep_search(self, query: str, num: int = 5, use_proxy: bool = True) -> List[Dict]:
        """深度搜索：Jina 优先， Bing 降级，DuckDuckGo 保底"""
        results = self.search_jina(query, num)
        if results:
            return results
        
        results = self.search_bing(query, num)
        if results:
            return results
        
        return self.search_ddg(query, num)

    def search_and_display(self, query: str, num: int = 5) -> None:
        """搜索并显示结果"""
        print(f"🔍 搜索: {query}\n")
        
        results = self.deep_search(query, num)
        
        if not results:
            print("⚠️ 未找到结果，尝试直接搜索网页...")
            results = self.search_ddg(query, num)
        
        if results:
            print(f"📋 找到 {len(results)} 条结果（来源: {self.last_source or 'bing'}）:\n")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['title']}")
                print(f"     🔗 {r['url']}")
                if r.get('description'):
                    print(f"     📝 {r['description']}...")
                print()
        else:
            print("❌ 搜索失败")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="搜索工具 v3.0（修复版）")
    parser.add_argument("query", nargs="?", help="搜索关键词")
    parser.add_argument("-n", "--num", type=int, default=5, help="结果数量 (默认5)")
    parser.add_argument("-j", "--json", action="store_true", help="JSON格式输出")
    parser.add_argument("-p", "--proxy", default="auto", 
                       help="代理设置: auto/none/具体URL (默认auto)")
    
    args = parser.parse_args()
    
    if not args.query:
        parser.print_help()
        return
    
    searcher = SearchMaster(proxy=args.proxy)
    
    if args.json:
        results = searcher.deep_search(args.query, args.num)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        searcher.search_and_display(args.query, args.num)

if __name__ == "__main__":
    main()
