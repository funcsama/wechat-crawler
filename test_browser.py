import asyncio
from playwright.async_api import async_playwright

async def test_wechat():
    url = "https://mp.weixin.qq.com/s/hz0SosxuMSHlNgzB3yWrjQ"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=15000)
            content = await page.content()
            print(f"Page length: {len(content)}")
            print("Title:", await page.title())
            text = await page.inner_text('body')
            print(f"Text length: {len(text)}")
            print("First 500 chars:", text[:500])
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

asyncio.run(test_wechat())
