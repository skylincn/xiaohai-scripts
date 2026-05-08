#!/usr/bin/env python3
"""
小红书登录脚本 - 获取 Cookies
"""
import sys
import time
import json
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

PHONE = "18601122987"
PASSWORD = "Lin99800"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            locale="zh-CN",
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        print("[1] 打开登录页...")
        page.goto("https://www.xiaohongshu.com/login", wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)
        page.screenshot(path="/tmp/xhs_step1.png")
        
        body = page.evaluate("document.body.innerText")
        print("[页面内容]:")
        print(body[:600])
        print("---")

        # 尝试找手机号输入框
        inputs = page.query_selector_all("input")
        print(f"[找到 {len(inputs)} 个输入框]:")
        for inp in inputs:
            print(f"  type={inp.get_attribute('type')} placeholder={inp.get_attribute('placeholder')} name={inp.get_attribute('name')}")

        # 查找所有可点击元素
        clickables = page.query_selector_all("a, button, [class*='btn'], [class*='tab']")
        print(f"[找到 {len(clickables)} 个可点击元素]:")
        for c in clickables:
            text = c.text_content() or ""
            if text.strip() and len(text.strip()) < 30:
                print(f"  {c.tag_name}: {text.strip()[:40]}")

        input("\n[按回车结束浏览器]")
        browser.close()

if __name__ == "__main__":
    main()
