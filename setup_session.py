"""
One-time LinkedIn session setup.

Run this once to log in and save your session. After that, quick_test.py
and the full tool will work without any popups or manual cookie hunting.

Usage:
    python setup_session.py
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

SESSION_FILE = Path("session.json")


async def main():
    print("\n=== LinkedIn Session Setup ===\n")
    print("A browser window will open.")
    print("⚠️  IMPORTANT: Use your LinkedIn email + password to log in.")
    print("    Do NOT click 'Continue with Google' — Google blocks automated browsers.")
    print("\nOnce you see your LinkedIn feed, come back here and press Enter.\n")

    async with async_playwright() as pw:
        # Launch a VISIBLE (headed) browser so the user can log in
        browser = await pw.chromium.launch(
            headless=False,
            args=["--no-sandbox"],
            slow_mo=50,
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await page.goto("https://www.linkedin.com/login")

        # Wait for the user to log in manually
        print("Waiting for you to log in... (press Enter in this terminal once you see your LinkedIn feed)")
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Verify login
        current_url = page.url
        if "feed" not in current_url and "mynetwork" not in current_url and "jobs" not in current_url:
            # Navigate to feed to confirm
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)

        if "login" in page.url or "authwall" in page.url:
            print("\n[setup] Not logged in yet. Please log in and re-run this script.")
            await browser.close()
            return

        # Save cookies
        cookies = await context.cookies()
        li_at = next((c for c in cookies if c["name"] == "li_at"), None)
        if not li_at:
            print("\n[setup] Could not find li_at cookie. Make sure you are fully logged in.")
            await browser.close()
            return

        SESSION_FILE.write_text(json.dumps({
            "cookies": cookies,
            "saved_at": datetime.utcnow().isoformat(),
        }, indent=2))

        print(f"\n[setup] Session saved to {SESSION_FILE} ({len(cookies)} cookies)")
        print("[setup] You can now run:  venv/bin/python quick_test.py")
        await browser.close()


asyncio.run(main())
