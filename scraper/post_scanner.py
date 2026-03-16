"""
post_scanner.py — Visit LinkedIn post URLs and extract name, profile URL, email.

Usage (standalone test):
    python -m scraper.post_scanner
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Page

from scraper.browser import get_browser_context, _human_delay
from scraper.email_extractor import extract_emails


@dataclass
class ScannedPost:
    post_url: str
    author_name: str = ""
    author_title: str = ""
    linkedin_profile_url: str = ""
    post_text: str = ""
    emails: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def has_email(self) -> bool:
        return bool(self.emails)


# CSS selectors for LinkedIn post elements
# LinkedIn frequently changes these — update if extraction breaks
_SELECTORS = {
    "author_name": [
        ".update-components-actor__name span[aria-hidden='true']",
        ".feed-shared-actor__name",
        ".update-components-actor__name",
    ],
    "author_title": [
        ".update-components-actor__description span[aria-hidden='true']",
        ".feed-shared-actor__description",
    ],
    "author_link": [
        ".update-components-actor__meta-link",
        ".feed-shared-actor__container-link",
        "a.app-aware-link[href*='/in/']",
    ],
    "post_text": [
        ".update-components-text span[dir='ltr']",
        ".feed-shared-update-v2__description",
        ".feed-shared-text",
    ],
}


async def _try_selectors(page: Page, selectors: list[str]) -> str:
    """Try a list of CSS selectors in order; return first non-empty text found."""
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        except Exception:
            continue
    return ""


async def _try_link_selectors(page: Page, selectors: list[str]) -> str:
    """Try selectors and return href attribute."""
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                href = await el.get_attribute("href")
                if href and "/in/" in href:
                    return href.split("?")[0].rstrip("/")
        except Exception:
            continue
    return ""


async def _js_extract(page: Page) -> dict:
    """
    JS-based extraction that doesn't rely on specific class names.
    Searches for structural patterns that LinkedIn uses regardless of CSS class churn.
    """
    return await page.evaluate("""
        () => {
            // Author profile link: first /in/ link in the actor/header area
            const allLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'));
            const authorLink = allLinks.find(a =>
                a.closest('[class*="actor"]') ||
                a.closest('[class*="author"]') ||
                a.closest('[class*="header"]') ||
                a.closest('header')
            ) || allLinks[0];

            // Post text: largest visible text block
            const textCandidates = [
                document.querySelector('[class*="commentary"]'),
                document.querySelector('[class*="update-components-text"]'),
                document.querySelector('[class*="feed-shared-text"]'),
                document.querySelector('[class*="attributed-text"]'),
                document.querySelector('[data-test-id="main-feed-activity-card__commentary"]'),
            ].filter(Boolean);
            const postEl = textCandidates[0] || null;

            // Author title: element near the author link with job-title-like text
            const titleCandidates = [
                document.querySelector('[class*="actor__description"]'),
                document.querySelector('[class*="actor__sub"]'),
                document.querySelector('[class*="author-info__headline"]'),
            ].filter(Boolean);

            return {
                authorHref: authorLink ? authorLink.href.split('?')[0] : '',
                authorName: authorLink ? (authorLink.innerText || authorLink.textContent || '').trim() : '',
                authorTitle: titleCandidates[0] ? titleCandidates[0].innerText.trim() : '',
                postText: postEl ? postEl.innerText.trim() : '',
            };
        }
    """)


async def scan_post(page: Page, post_url: str) -> ScannedPost:
    """Navigate to a single post URL and extract all fields."""
    result = ScannedPost(post_url=post_url)
    try:
        await page.goto(post_url, wait_until="load", timeout=30_000)
        # Wait for post content to be rendered
        try:
            await page.wait_for_selector(
                "[class*='update-components'], [class*='feed-shared'], "
                "[class*='actor'], main",
                timeout=15_000,
            )
        except Exception:
            pass
        _human_delay(1.5, 2.5)

        # Try CSS selectors first
        result.author_name = await _try_selectors(page, _SELECTORS["author_name"])
        result.author_title = await _try_selectors(page, _SELECTORS["author_title"])
        result.linkedin_profile_url = await _try_link_selectors(page, _SELECTORS["author_link"])
        result.post_text = await _try_selectors(page, _SELECTORS["post_text"])

        # JS fallback if CSS selectors missed
        if not result.author_name or not result.post_text:
            js = await _js_extract(page)
            result.author_name = result.author_name or js.get("authorName", "")
            result.author_title = result.author_title or js.get("authorTitle", "")
            result.linkedin_profile_url = result.linkedin_profile_url or js.get("authorHref", "")
            result.post_text = result.post_text or js.get("postText", "")

        # Debug dump when still empty — save HTML for selector inspection
        if not result.author_name and not result.post_text:
            try:
                html = await page.content()
                debug_path = Path(__file__).parent.parent / "debug_post.html"
                debug_path.write_text(html)
                print(f"[scanner]   ⚠ All selectors empty — HTML saved to debug_post.html")
            except Exception:
                pass

        # Extract emails from post text or full body
        full_text = result.post_text or await page.inner_text("body")
        result.emails = extract_emails(full_text)

    except Exception as e:
        result.error = str(e)

    return result


async def scan_posts(
    post_urls: list[str],
    log_fn=print,
) -> list[ScannedPost]:
    """
    Scan a list of post URLs, returning a ScannedPost for each.
    Reuses a single browser session for all posts.
    """
    results: list[ScannedPost] = []

    async with get_browser_context() as (ctx, page):
        for i, url in enumerate(post_urls, 1):
            log_fn(f"[scanner] [{i}/{len(post_urls)}] {url}")
            post = await scan_post(page, url)

            if post.error:
                log_fn(f"[scanner]   ERROR: {post.error}")
            else:
                log_fn(
                    f"[scanner]   author={post.author_name!r}  "
                    f"emails={post.emails}  "
                    f"profile={'yes' if post.linkedin_profile_url else 'no'}"
                )

            results.append(post)
            _human_delay(2.0, 4.5)

    return results


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    TEST_URLS = [
        # Replace with real post URLs to test
        "https://www.linkedin.com/posts/oscar-leung_jobsearch-opentowork-automation-activity-7424863134156275712-Y0Jx",
    ]

    async def _test():
        posts = await scan_posts(TEST_URLS)
        for p in posts:
            print(f"\nURL:     {p.post_url}")
            print(f"Name:    {p.author_name}")
            print(f"Title:   {p.author_title}")
            print(f"Profile: {p.linkedin_profile_url}")
            print(f"Emails:  {p.emails}")
            print(f"Text[:100]: {p.post_text[:100]!r}")
        print("\n[test] post_scanner.py OK")

    asyncio.run(_test())
