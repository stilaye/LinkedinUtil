"""
search_runner.py — Execute LinkedIn search queries and collect post URLs.

Usage (standalone test):
    python -m scraper.search_runner
"""

import asyncio
import json
import random
import time
from pathlib import Path

from playwright.async_api import Page

from scraper.browser import get_browser_context, _human_delay

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

# LinkedIn content search base URL
_SEARCH_BASE = "https://www.linkedin.com/search/results/content/"

# Known geo URNs for quick reference (add more as needed)
GEO_URNS = {
    "united states":   "103644278",
    "us":              "103644278",
    "united kingdom":  "101165590",
    "uk":              "101165590",
    "canada":          "101174742",
    "australia":       "101452733",
    "india":           "102713980",
    "germany":         "101282230",
    "singapore":       "102454443",
    "remote":          None,  # no geo URN for remote
}

# Valid datePosted values accepted by LinkedIn
_DATE_FILTER_MAP = {
    "24h":        "past-24h",
    "past-24h":   "past-24h",
    "7d":         "past-week",
    "week":       "past-week",
    "past-week":  "past-week",
    "month":      "past-month",
    "past-month": "past-month",
    "none":       None,
    "":           None,
}


def _build_search_url(query: str, date_filter: str | None, geo_urns: list[str]) -> str:
    """
    Build a LinkedIn content search URL with optional date and geo filters.

    Examples:
        date_filter="past-week"   → &datePosted=past-week
        geo_urns=["103644278"]    → &geoUrn=%5B%22urn%3Ali%3Ago_geo%3A103644278%22%5D
    """
    from urllib.parse import urlencode, quote

    params: dict[str, str] = {
        "keywords": query,
        "origin": "GLOBAL_SEARCH_HEADER",
        "sortBy": "date_posted",   # most recent first
    }

    if date_filter:
        mapped = _DATE_FILTER_MAP.get(date_filter.lower())
        if mapped:
            params["datePosted"] = mapped

    if geo_urns:
        # LinkedIn encodes geo URNs as a JSON array of URN strings
        urn_list = [f"urn:li:geo:{g}" for g in geo_urns if g]
        if urn_list:
            import json
            params["geoUrn"] = json.dumps(urn_list)

    return _SEARCH_BASE + "?" + urlencode(params, quote_via=quote)


def _load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text())


async def _extract_cards(page: Page) -> list[dict]:
    """
    Extract post data directly from the visible search result cards.

    LinkedIn uses hashed CSS class names (no stable class names).
    Reliable anchors:
      - Cards:     div[role="listitem"] containing [data-view-name*="feed"]
      - Name:      textContent of a[href*="/in/"]  (innerText is empty due to CSS)
      - Post text: [data-testid="expandable-text-box"]
      - Post URL:  a[href*="/feed/update/"]
    """
    return await page.evaluate("""
        () => {
            const results = [];

            // Every post card is a div[role="listitem"]
            const cards = document.querySelectorAll('div[role="listitem"]');

            cards.forEach(card => {
                // Only process cards that wrap a feed post
                if (!card.querySelector('[data-view-name*="feed"]')) return;

                // ── Author ──────────────────────────────────────────────────
                // There are TWO /in/ links per card: image link (no text) + name link (has text).
                // Skip the image link by finding the first /in/ link with non-empty textContent.
                // Use textContent (not innerText) — LinkedIn hides text via CSS so innerText = ''.
                let authorLink = null;
                let authorHref = '';
                let authorName = '';

                const allInLinks = card.querySelectorAll('a[href*="/in/"]');
                for (const link of allInLinks) {
                    const t = (link.textContent || '').replace(/\\s+/g, ' ').trim();
                    if (t.length > 2) { authorLink = link; break; }
                }

                if (authorLink) {
                    authorHref = authorLink.href.split('?')[0].replace(/\\/$/, '');

                    // Get ONLY the first span/p inside the link (the name element).
                    // The full textContent of the link includes headline, timestamp, etc.
                    const nameEl = authorLink.querySelector('span') ||
                                   authorLink.querySelector('p');
                    const raw = nameEl
                        ? (nameEl.textContent || '').replace(/\\s+/g, ' ').trim()
                        : '';

                    // Strip LinkedIn badge noise: degrees (1st, 2nd, 3rd+), buttons, emojis trail
                    authorName = raw
                        .replace(/Verified Profile\\s*/gi, '')
                        .replace(/Premium Profile\\s*/gi, '')
                        .replace(/\\b(1st\\+?|2nd\\+?|3rd\\+?|Follow(?:ing)?|Connect|\\+\\s*Follow|Hiring)\\b/gi, '')
                        .replace(/\\s*\\+\\s*$/, '')   // trailing " +" from 3rd+ degree
                        .replace(/\\s+/g, ' ')
                        .trim();
                }

                // ── Post text ───────────────────────────────────────────────
                // data-testid="expandable-text-box" is stable across LinkedIn's redesigns
                const textBox = card.querySelector('[data-testid="expandable-text-box"]');
                const postText = textBox ? (textBox.textContent || '').trim() : '';

                // ── Post URL ────────────────────────────────────────────────
                const postLink = card.querySelector('a[href*="/feed/update/"], a[href*="/posts/"]');
                const postUrl = postLink ? postLink.href.split('?')[0] : '';

                // ── Author title ────────────────────────────────────────────
                // The headline sits as a leaf text node AFTER the name node inside the actor block.
                // We skip any text that matches or contains the author name / badge noise.
                const badgeRE = /Verified Profile|Premium Profile|1st|2nd|3rd|Follow|Connect|Hiring|Feed post|Promoted/i;
                let authorTitle = '';
                if (authorLink) {
                    const actorBlock = authorLink.closest('div') || card;
                    const leaves = Array.from(actorBlock.querySelectorAll('span, p'))
                        .filter(el => el.children.length === 0);  // leaf nodes only
                    for (const el of leaves) {
                        const t = (el.textContent || '').replace(/\\s+/g, ' ').trim();
                        if (
                            t.length > 5 && t.length < 150 &&
                            !t.includes(authorName) &&
                            !badgeRE.test(t)
                        ) {
                            authorTitle = t;
                            break;
                        }
                    }
                }

                if (authorHref || postText) {
                    results.push({
                        author_name: authorName,
                        author_href: authorHref,
                        author_title: authorTitle,
                        post_text: postText,
                        post_url: postUrl,
                    });
                }
            });

            return results;
        }
    """)


async def _scroll_and_collect(page: Page, max_posts: int) -> tuple[list[str], list[dict]]:
    """
    Scroll through a LinkedIn search results page.
    Returns (post_urls, extracted_cards).
    - post_urls: permalink hrefs when LinkedIn exposes them
    - extracted_cards: author/text data pulled directly from result cards
    """
    post_urls: set[str] = set()
    all_cards: list[dict] = []
    seen_profiles: set[str] = set()
    last_count = -1
    stale_scrolls = 0

    while len(all_cards) < max_posts and stale_scrolls < 4:
        # Extract cards directly from the page
        cards = await _extract_cards(page)
        for card in cards:
            key = card.get("author_href") or card.get("post_text", "")[:80]
            if key and key not in seen_profiles:
                seen_profiles.add(key)
                all_cards.append(card)
                if card.get("post_url"):
                    post_urls.add(card["post_url"])

        if len(all_cards) == last_count:
            stale_scrolls += 1
        else:
            stale_scrolls = 0
        last_count = len(all_cards)

        scroll_distance = random.randint(600, 1200)
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        _human_delay(2.0, 4.0)

    return list(post_urls), all_cards[:max_posts]


async def run_searches(
    queries: list[str] | None = None,
    max_posts_per_run: int | None = None,
    log_fn=print,
) -> dict:
    """
    Execute all configured search queries on LinkedIn.

    Returns:
        {
            "post_urls": [...],        # deduplicated across all queries
            "per_query": {             # per-query stats
                "query text": {"found": N, "status": "ok"|"failed"}
            }
        }
    """
    config = _load_config()
    queries = queries or config.get("queries", [])
    max_posts = max_posts_per_run or config.get("max_posts_per_run", 100)
    per_query_cap = max(10, max_posts // len(queries)) if queries else max_posts

    # Filters from config
    date_filter = config.get("date_filter", "")
    geo_urns    = config.get("geo_urns", [])

    all_urls: set[str] = set()
    all_cards: list[dict] = []
    seen_profiles: set[str] = set()
    per_query: dict[str, dict] = {}

    async with get_browser_context() as (ctx, page):
        for query in queries:
            log_fn(f"[search] Running query: '{query}'")
            url = _build_search_url(query, date_filter, geo_urns)
            log_fn(f"[search]   URL: {url}")
            try:
                await page.goto(url, wait_until="load", timeout=30_000)
                try:
                    await page.wait_for_selector(
                        "li.reusable-search__result-container, "
                        "[data-view-name*='search-result'], "
                        ".scaffold-layout__main",
                        timeout=15_000,
                    )
                except Exception:
                    pass
                _human_delay(2.0, 3.0)

                urls, cards = await _scroll_and_collect(page, per_query_cap)

                new_urls = [u for u in urls if u not in all_urls]
                all_urls.update(new_urls)

                new_cards = [
                    c for c in cards
                    if (c.get("author_href") or c.get("post_text", "")[:80])
                    not in seen_profiles
                ]
                for c in new_cards:
                    seen_profiles.add(c.get("author_href") or c.get("post_text", "")[:80])
                all_cards.extend(new_cards)

                log_fn(f"[search]   → {len(new_cards)} posts found (total: {len(all_cards)})")
                per_query[query] = {"found": len(new_cards), "status": "ok"}

            except Exception as e:
                log_fn(f"[search]   → FAILED: {e}")
                per_query[query] = {"found": 0, "status": "failed"}

            _human_delay(3.0, 6.0)

    return {"post_urls": list(all_urls), "extracted_posts": all_cards, "per_query": per_query}


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _test():
        result = await run_searches(
            queries=["hiring QA engineer remote"],
            max_posts_per_run=10,
        )
        print(f"\n[test] Found {len(result['post_urls'])} post URLs:")
        for u in result["post_urls"][:5]:
            print(f"  {u}")
        print("[test] search_runner.py OK")

    asyncio.run(_test())
