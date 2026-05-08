#!/usr/bin/env python3
"""
read_xiaohongshu.py - 小红书笔记内容读取器 v2.0
使用 Playwright 浏览器渲染获取笔记内容

Cookie来源：Chrome DevTools → Application → Cookies → xiaohongshu.com
"""

import re, sys, json, time, html2text
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

h2t = html2text.HTML2Text()
h2t.body_width = 0

# ─── Cookies（2026-05-03 最新）───
COOKIES = [
    {'name': 'acw_tc', 'value': '0a00da1317777919452065403e118efa70ab843762962707940a95999d5d05', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'ets', 'value': '1777791946757', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'gid', 'value': 'yjfdS0Y2iDl2yjfdS0Y287kuqDi7lhI3dTiDYIIjWS6yFAq8IFYT9q8884yq2Yj8yff802y2', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'id_token', 'value': 'VjEAAFBYrp6gA/dahqBf7/U1+6csgWv1OryIGs9spD7i6CRqdBS9DRg4N+z72D9qc7O+Sh2Ej/Zw1gA2R6sR2Cr3h8kqL9FMJt9upwEbQbPXRvgIe/r228tJgksF+ejJ9iJU0C2M', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'loadts', 'value': '1777791946808', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'sec_poison_id', 'value': '50cccd99-dd85-4c7a-a2e6-23ac69c19de0', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'unread', 'value': '{"ub":"69eda4c40000000035025396","ue":"69eb3487000000002202925b","uc":33}', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'web_session', 'value': '040069b2c9c5c4cb730d91bbc33b4bca6b1c38', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'webBuild', 'value': '6.8.1', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'webId', 'value': 'afe7848778a28871506c3f5e1c438048', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'websectiga', 'value': '634d3ad75ffb42a2ade2c5e1705a73c845837578aeb31ba0e442d75c648da36a', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'xsecappid', 'value': 'xhs-pc-web', 'domain': '.xiaohongshu.com', 'path': '/'},
    {'name': 'a1', 'value': '199fa46e26bx9zclk02ftrom6ui8pml8vhhgpzamn30000363585', 'domain': '.xiaohongshu.com', 'path': '/'},
]


def extract_note_id(url_or_id: str) -> str:
    m = re.search(r'/discovery/item/([a-f0-9]{24})', url_or_id, re.IGNORECASE)
    if m: return m.group(1).lower()
    m = re.search(r'/([a-f0-9]{24})', url_or_id, re.IGNORECASE)
    if m: return m.group(1).lower()
    m = re.match(r'^([a-f0-9]{24})$', url_or_id.strip(), re.IGNORECASE)
    if m: return m.group(1).lower()
    return ""


def read_note(url_or_id: str) -> dict:
    note_id = extract_note_id(url_or_id)
    if not note_id:
        return {"error": f"无法提取笔记ID: {url_or_id}"}

    target = f"https://www.xiaohongshu.com/discovery/item/{note_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )
        for c in COOKIES:
            context.add_cookies([c])

        page = context.new_page()
        page.set_default_timeout(30_000)

        try:
            # Visit homepage first (sets fresh sec_poison_id)
            page.goto("https://www.xiaohongshu.com/", wait_until="domcontentloaded", timeout=20_000)
            time.sleep(4)

            # Navigate to note
            r = page.goto(target, wait_until="domcontentloaded", timeout=20_000)
            time.sleep(6)

            body_text = page.evaluate("document.body.innerText")
            
            # Check for block page
            if "App内打开" in body_text or "仅支持在小红书 APP" in body_text:
                return {"error": "内容需在APP内查看（反爬）", "note_id": note_id, "url": target}
            
            if r.url.endswith("/404") or "/404?" in r.url:
                return {"error": "笔记不存在/已删除", "note_id": note_id}

            # Extract structured data (JSON-LD)
            result = {"note_id": note_id, "platform": "xiaohongshu", "url": target}
            
            scripts = page.query_selector_all('script[type="application/ld+json"]')
            for s in scripts:
                txt = s.text_content() or ""
                if '"@type"' in txt and ('Article' in txt or 'BlogPosting' in txt):
                    try:
                        data = json.loads(txt)
                        result["title"] = data.get("headline", data.get("name", ""))
                        result["content"] = data.get("articleBody", "")
                        result["author"] = data.get("author", {}).get("name", "") if isinstance(data.get("author"), dict) else str(data.get("author", ""))
                        break
                    except:
                        pass

            # DOM fallback
            if not result.get("content"):
                for sel in ["#detail-content", ".note-content", ".detail-content", "article"]:
                    el = page.query_selector(sel)
                    if el:
                        txt = el.text_content().strip()
                        if len(txt) > 50:
                            result["content"] = txt
                            break

            if not result.get("title"):
                for sel in ["#detail-title", "h1.title"]:
                    el = page.query_selector(sel)
                    if el:
                        result["title"] = el.text_content().strip()
                        break

            # Images
            images = []
            for sel in ["#detail-content img", ".note-content img", "article img"]:
                imgs = page.query_selector_all(sel)
                for img in imgs:
                    src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                    if src and not src.startswith("data:") and len(src) > 20:
                        images.append(src)
                        if len(images) >= 20: break
            if images:
                result["images"] = list(dict.fromkeys(images))

            # Convert to markdown
            html_el = page.query_selector("#detail-content, .note-content, .detail-content, article")
            if html_el and result.get("content"):
                result["content_md"] = h2t.handle(html_el.inner_html()).strip()

            if not result.get("content") and not result.get("title"):
                return {"error": "未能提取内容（可能是反爬或页面结构变化）", "note_id": note_id, "body_preview": body_text[:200]}

            return result

        except PWTimeout:
            return {"error": "页面加载超时", "note_id": note_id}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "note_id": note_id}
        finally:
            browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 read_xiaohongshu.py <小红书链接或笔记ID>")
        sys.exit(1)

    result = read_note(sys.argv[1])

    if "error" in result and "body_preview" not in result:
        print(f"❌ {result['error']}", file=sys.stderr)
        sys.exit(1)
    elif "error" in result and "body_preview" in result:
        print(f"⚠️ {result['error']}", file=sys.stderr)
        print(f"页面预览: {result['body_preview']}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📕 【小红书】{result.get('title', '无标题')}")
    if result.get('author'): print(f"👤 {result['author']}")
    print(f"🔗 {result.get('url', '')}")
    print(f"\n📝 正文:\n{result.get('content', result.get('content_md', '(无正文)'))[:500]}")
    if result.get('images'):
        print(f"\n🖼 共 {len(result['images'])} 张图片")
    
    out = f"/tmp/xhs_note_{result['note_id']}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n💾 完整数据: {out}")