#!/usr/bin/env python3.11
"""Try to fetch WeChat article via Playwright headless browser."""
import sys
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed")
    sys.exit(1)

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
)
REFERER = "https://mp.weixin.qq.com/"

url = "https://mp.weixin.qq.com/s/hz0SosxuMSHlNgzB3yWrjQ"

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ]
    )
    ctx = browser.new_context(
        user_agent=UA,
        locale="zh-CN",
        extra_http_headers={"Referer": REFERER},
    )
    page = ctx.new_page()

    print("Navigating...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print("goto exception:", e)

    print("Current URL:", page.url)
    print("Title:", page.title())

    # Wait for content
    try:
        page.wait_for_selector("#js_content", timeout=10000)
        print("Found #js_content!")
    except Exception as e:
        print("No #js_content found:", e)

    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    html = page.content()
    print("HTML length:", len(html))
    print("First 500 chars:", html[:500])
    print("\nLast 300 chars:", html[-300:])

    # Check markers
    has_js = 'id="js_content"' in html
    has_env = "环境异常" in html
    print("\nhas js_content:", has_js)
    print("has 环境异常:", has_env)

    browser.close()
