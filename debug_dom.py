"""
debug_dom.py — Dump LinkedIn search results page DOM to a file
so we can fix the CSS selectors.

Usage:
    venv/bin/python debug_dom.py "hiring quality engineer Apple"
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
load_dotenv()


async def main():
    query = " ".join(sys.argv[1:]) or "hiring quality engineer Apple"
    url = f"https://www.linkedin.com/search/results/content/?keywords={quote_plus(query)}&origin=GLOBAL_SEARCH_HEADER"

    from scraper.browser import get_browser_context, _human_delay

    async with get_browser_context() as (ctx, page):
        print(f"[debug] Navigating to search page...")
        await page.goto(url, wait_until="load", timeout=30_000)

        # Wait up to 15s for *any* content
        try:
            await page.wait_for_selector("main, [role='main'], .scaffold-layout__main", timeout=15_000)
        except Exception:
            pass

        _human_delay(3.0, 4.0)  # let JS render cards

        out = Path("debug_dom.html")
        shot = Path("debug_screenshot.png")

        # 0. Screenshot
        await page.screenshot(path=str(shot), full_page=False)
        print(f"[debug] Screenshot saved → {shot}")

        # 1. Save full page HTML
        html = await page.content()
        out.write_text(html, encoding="utf-8")
        print(f"[debug] Full HTML saved → {out} ({len(html):,} bytes)")

        # 2. Print all unique class names that contain keywords we care about
        classes = await page.evaluate("""
            () => {
                const all = new Set();
                document.querySelectorAll('*[class]').forEach(el => {
                    el.className.toString().split(/\\s+/).forEach(c => {
                        if (c && (
                            c.includes('result') || c.includes('search') ||
                            c.includes('feed') || c.includes('update') ||
                            c.includes('actor') || c.includes('post') ||
                            c.includes('text') || c.includes('comment') ||
                            c.includes('card') || c.includes('content')
                        )) {
                            all.add(c);
                        }
                    });
                });
                return Array.from(all).sort();
            }
        """)
        print("\n[debug] Relevant CSS classes found on page:")
        for c in classes:
            print(f"  .{c}")

        # 3. Count list items
        li_count = await page.evaluate("() => document.querySelectorAll('li').length")
        print(f"\n[debug] Total <li> elements: {li_count}")

        # 4. Try each selector and report count
        selectors = [
            "li.reusable-search__result-container",
            "[data-view-name*='search-result']",
            ".search-results__result-container",
            "[class*='reusable-search']",
            "[class*='search-result']",
            "[class*='entity-result']",
            "a[href*='/in/']",
            "a[href*='/feed/update/']",
            "a[href*='/posts/']",
            "[class*='update-components']",
            "[class*='feed-shared']",
            "[class*='attributed-text']",
            "[class*='commentary']",
            "[class*='actor__name']",
        ]
        print("\n[debug] Selector hit counts:")
        for sel in selectors:
            count = await page.evaluate(
                f"() => document.querySelectorAll({sel!r}).length"
            )
            print(f"  {count:3d}  {sel}")

        # 5. Dump first author /in/ link found
        first_author = await page.evaluate("""
            () => {
                const a = document.querySelector('a[href*="/in/"]');
                return a ? {href: a.href, text: a.innerText.trim().slice(0,80)} : null;
            }
        """)
        print(f"\n[debug] First /in/ link: {first_author}")

        print("\n[debug] Done. Open debug_dom.html in a browser to inspect the full structure.")


asyncio.run(main())
