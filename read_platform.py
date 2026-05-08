#!/usr/bin/env python3
"""
read_platform.py v2.0 - 小红书/微信公众号 内容读取器
使用 xhs 库 + Playwright 混合方案
"""

import re
import sys
import time
import json
import html2text
import requests
from pathlib import Path

# ─── xhs 库（用于小红书） ───
import xhs
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright.sync_api import Page, Browser

HEADLESS = True
TIMEOUT = 25_000

# ─── HTML → Markdown 转换器 ───
h2t = html2text.HTML2Text()
h2t.body_width = 0  # 不换行
h2t.ignore_links = False
h2t.ignore_images = False


# ─── 平台检测 ───

def detect_platform(url: str) -> str:
    if "xiaohongshu.com" in url or "xhslink.com" in url:
        return "xiaohongshu"
    if "mp.weixin.qq.com" in url:
        return "wechat"
    return "unknown"


def extract_note_id(url: str) -> str:
    """从 URL 提取小红书笔记 ID"""
    match = re.search(r'/discovery/item/([a-f0-9]+)', url)
    if match:
        return match.group(1)
    # 短链接
    match = re.search(r'/([a-f0-9]{24})', url)
    if match:
        return match.group(1)
    return ""


def extract_wechat_id(url: str) -> str:
    """从 URL 提取微信公众号文章 ID"""
    match = re.search(r'/s/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return ""


# ─── 小红书读取方案 1：xhs 库 + HTML 解析 ───

def read_xiaohongshu_html(note_id: str = None, url: str = None) -> dict:
    """使用 xhs 库的 HTML 解析方式（无需登录）"""
    if url:
        note_id = extract_note_id(url)
    if not note_id:
        return {"error": "无法提取笔记 ID"}

    try:
        client = xhs.XhsClient()
        note = client.get_note_by_id_from_html(note_id)
        if not note:
            return {"error": "未找到笔记"}

        # 解析返回的 HTML
        html = note.get("html", "")
        if not html:
            return {"error": "无 HTML 内容"}

        # 转换为 markdown
        content_md = h2t.handle(html)

        return {
            "title": note.get("title", ""),
            "author": note.get("author", {}).get("name", "") if isinstance(note.get("author"), dict) else str(note.get("author", "")),
            "content": content_md.strip(),
            "liked": note.get("liked_count", note.get("interact_info", {}).get("liked_count", "")),
            "collected": note.get("collected", ""),
            "platform": "xiaohongshu",
            "note_id": note_id,
        }
    except json.JSONDecodeError as e:
        return {"error": f"HTML 解析失败: {e}"}
    except Exception as e:
        return {"error": f"读取失败: {type(e).__name__}: {e}"}


# ─── 小红书读取方案 2：Playwright 渲染（备用） ───

def read_xiaohongshu_browser(note_id: str = None, url: str = None) -> dict:
    """使用 Playwright 浏览器渲染（尝试绕过反爬）"""
    if url:
        note_id = extract_note_id(url)
    if not note_id:
        return {"error": "无法提取笔记 ID"}

    target_url = url or f"https://www.xiaohongshu.com/discovery/item/{note_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--single-process",
            ]
        )
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        page = context.new_page()

        # 移除 webdriver 检测
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)

        page.set_default_timeout(TIMEOUT)

        try:
            # 先访问主页获取 cookie
            page.goto("https://www.xiaohongshu.com/", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)

            # 再访问笔记页
            r = page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(5)

            if r.url.endswith("/404") or "404" in page.title():
                return {"error": "笔记不存在或已被删除"}

            # 等待内容加载
            try:
                page.wait_for_selector("body", timeout=5000)
            except:
                pass

            # 提取正文
            content_parts = []

            # 方法1：JSON-LD
            try:
                scripts = page.query_selector_all('script[type="application/ld+json"]')
                for s in scripts:
                    txt = s.text_content() or ""
                    if '"@type"' in txt and '"Article"' in txt:
                        data = json.loads(txt)
                        content_parts.append(data.get("articleBody", ""))
                        break
            except:
                pass

            # 方法2：DOM 提取
            if not content_parts:
                selectors = [
                    "#detail-content",
                    ".note-content",
                    ".detail-content",
                    "article",
                    ".rich_media_content",
                ]
                for sel in selectors:
                    el = page.query_selector(sel)
                    if el:
                        content_parts.append(el.text_content().strip())
                        break

            # 标题
            title = ""
            for sel in ["#detail-title", "h1.title", ".note-content .title", ".rich_media_title"]:
                el = page.query_selector(sel)
                if el:
                    title = el.text_content().strip()
                    break

            # 作者
            author = ""
            for sel in [".author-info .name", ".user-nickname", "#js_name"]:
                el = page.query_selector(sel)
                if el:
                    author = el.text_content().strip()
                    break

            result = {
                "title": title,
                "author": author,
                "content": "\n".join(content_parts),
                "platform": "xiaohongshu",
                "note_id": note_id,
            }

        except PWTimeoutError:
            result = {"error": "页面加载超时"}
        except Exception as e:
            result = {"error": str(e)}
        finally:
            browser.close()

    return result


# ─── 微信公众号读取：Playwright ───

def read_wechat_browser(url: str) -> dict:
    """使用 Playwright 读取微信公众号文章"""
    wechat_id = extract_wechat_id(url)
    if not wechat_id:
        return {"error": "无法提取文章 ID"}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            locale="zh-CN",
        )
        page = context.new_page()
        page.set_default_timeout(TIMEOUT)

        try:
            r = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            time.sleep(5)

            if r.url.endswith("/404") or "参数错误" in page.evaluate("document.body.innerText"):
                return {"error": "文章不存在或参数错误"}

            # 提取标题
            title = ""
            for sel in ["#activity-name", ".rich_media_title", "h1"]:
                el = page.query_selector(sel)
                if el:
                    title = el.text_content().strip()
                    break

            # 提取作者
            author = ""
            for sel in ["#js_name", ".rich_media_meta_nickname"]:
                el = page.query_selector(sel)
                if el:
                    author = el.text_content().strip()
                    break

            # 提取正文
            content = ""
            for sel in ["#js_content", ".rich_media_content"]:
                el = page.query_selector(sel)
                if el:
                    content = el.text_content().strip()
                    break

            if not content:
                body = page.evaluate("document.body.innerText")
                if "登录" in body:
                    return {"error": "需要微信授权登录"}
                content = body

            # 转换为 markdown
            html_content = page.query_selector("#js_content")
            if html_content:
                content_md = h2t.handle(html_content.inner_html())
            else:
                content_md = content

            return {
                "title": title,
                "author": author,
                "content": content_md.strip() if html_content else content,
                "platform": "wechat",
                "article_id": wechat_id,
            }

        except PWTimeoutError:
            return {"error": "页面加载超时"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            browser.close()

    return result


# ─── 微信公众号读取：备用方案（搜狗微信搜索） ───

def read_wechat_via_sogou(url_or_keyword: str) -> dict:
    """通过搜狗微信搜索读取公众号文章（无需登录）"""
    try:
        keyword = url_or_keyword
        # 如果是 URL，先提取关键词
        if "mp.weixin.qq.com" in url_or_keyword:
            article_id = extract_wechat_id(url_or_keyword)
            keyword = article_id

        s = requests.Session()
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html',
            'Referer': 'https://weixin.sogou.com/',
        })

        # 搜索
        r = s.get(
            'https://weixin.sogou.com/weixin',
            params={'type': 'article', 'query': keyword, 'ie': 'utf8'},
            timeout=15
        )

        if r.status_code != 200:
            return {"error": f"搜狗搜索失败: {r.status_code}"}

        # 提取文章链接
        links = re.findall(r'href="(https://mp\.weixin\.qq\.com/s/[^"]+)"', r.text)
        if not links:
            return {"error": "搜狗未找到对应文章"}

        # 访问第一个结果
        article_url = links[0]
        r2 = s.get(article_url, timeout=15)
        if r2.status_code != 200:
            return {"error": f"文章页面加载失败: {r2.status_code}"}

        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip = False

            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self.skip = True

            def handle_endtag(self, tag):
                if tag in ('script', 'style'):
                    self.skip = False

            def handle_data(self, data):
                if not self.skip:
                    self.text.append(data.strip())

        parser = TextExtractor()
        parser.feed(r2.text)
        content = ' '.join(t for t in parser.text if t)

        # 提取标题
        title_match = re.search(r'<h1[^>]*id="activity-name"[^>]*>([^<]+)</h1>', r2.text)
        title = title_match.group(1).strip() if title_match else keyword

        return {
            "title": title,
            "author": "",
            "content": content,
            "platform": "wechat",
            "source": "sogou",
        }

    except Exception as e:
        return {"error": f"搜狗读取失败: {type(e).__name__}: {e}"}


# ─── 主入口 ───

def read_page(url: str) -> dict:
    """统一读取入口"""
    platform = detect_platform(url)

    if platform == "unknown":
        return {"error": f"不支持的平台: {url}"}

    print(f"[read_platform] 检测到平台: {platform}", file=sys.stderr)

    if platform == "xiaohongshu":
        # 优先尝试 HTML 解析方式（xhs 库）
        note_id = extract_note_id(url)
        print(f"[read_platform] 笔记ID: {note_id}", file=sys.stderr)

        # 方法1：xhs 库 HTML 解析
        result = read_xiaohongshu_html(note_id=note_id, url=url)
        if "error" not in result:
            return result

        print(f"[read_platform] HTML方式失败，尝试浏览器: {result.get('error')}", file=sys.stderr)

        # 方法2：Playwright 浏览器
        result = read_xiaohongshu_browser(note_id=note_id, url=url)
        return result

    elif platform == "wechat":
        # 优先尝试搜狗（无需浏览器）
        result = read_wechat_via_sogou(url)
        if "error" not in result:
            return result

        print(f"[read_platform] 搜狗方式失败，尝试浏览器: {result.get('error')}", file=sys.stderr)

        # 备用：Playwright
        result = read_wechat_browser(url)
        return result

    return {"error": "未知平台"}


# ─── CLI ───

def main():
    if len(sys.argv) < 2:
        print("用法: python3 read_platform.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    result = read_page(url)

    if "error" in result:
        print(f"❌ {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📕 {result.get('title', '无标题')}")
    if result.get('author'):
        print(f"👤 {result['author']}")
    print(f"\n📝 正文:\n{result.get('content', '(无正文)')}")

    return result


if __name__ == "__main__":
    main()