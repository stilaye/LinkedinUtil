import asyncio
from dotenv import load_dotenv
load_dotenv()

from scraper.browser import _read_chrome_cookies
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug():
    cookies = _read_chrome_cookies()
    print(f"li_at present: {any(c['name']=='li_at' for c in cookies)}")

    stealth = Stealth()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        await stealth.apply_stealth_async(context)
        await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        print(f"URL after goto feed: {page.url}")
        title = await page.title()
        print(f"Page title: {title}")
        await browser.close()

asyncio.run(debug())
