"""
Quick end-to-end test — login → search → scan → print results.

Usage:
    python quick_test.py                            # default query
    python quick_test.py "hiring quality engineer"  # custom query
"""
import asyncio
import csv
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _split_headline(headline: str) -> tuple[str, str]:
    """
    Split a LinkedIn headline like 'Software Engineering Manager at Apple | Ex-Google'
    into (role, company).  Handles ' at ', ' @ ', ' · ', ' | '.
    """
    if not headline:
        return "", ""
    # Take only the first segment (before |)
    first = headline.split("|")[0].split("·")[0].strip()
    for sep in (" at ", " @ ", ", "):
        if sep in first:
            parts = first.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return first.strip(), ""


async def main():
    query = " ".join(sys.argv[1:]) or "hiring quality engineer Apple"
    print(f"\n[quick_test] Query: {query!r}\n")

    # 1. Search — extract post data directly from search result cards
    from scraper.search_runner import run_searches
    from scraper.email_extractor import extract_emails
    result = await run_searches(queries=[query], max_posts_per_run=10)

    cards = result.get("extracted_posts", [])
    print(f"[quick_test] Found {len(cards)} posts\n")

    if not cards:
        print("No posts found. Try a different query.")
        return

    # 2. Print structured output
    print("=" * 60)
    found_emails = 0
    for i, c in enumerate(cards, 1):
        emails = extract_emails(c.get("post_text", ""))
        if emails:
            found_emails += 1

        # Split "Job Title at Company | extra" → role + company
        headline = c.get("author_title") or ""
        role, company = _split_headline(headline)

        print(f"[{i}] {c.get('author_name') or '(unknown)'}")
        print(f"    Role    : {role or '—'}")
        print(f"    Company : {company or '—'}")
        print(f"    Profile : {c.get('author_href') or '—'}")
        print(f"    Post URL: {c.get('post_url') or '—'}")
        print(f"    Email   : {', '.join(emails) if emails else '—'}")
        snippet = textwrap.shorten(c.get("post_text") or "", width=200, placeholder="…")
        print(f"    Post    : {snippet}")
        print()

    print(f"[quick_test] Done — {len(cards)} posts found, {found_emails} with email")

    # ── Save to CSV ──────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"leads_{timestamp}.csv"
    fieldnames = ["name", "role", "company", "linkedin_profile_url", "post_url", "email", "post_snippet"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in cards:
            emails = extract_emails(c.get("post_text", ""))
            headline = c.get("author_title") or ""
            role, company = _split_headline(headline)
            writer.writerow({
                "name":                c.get("author_name") or "",
                "role":                role,
                "company":             company,
                "linkedin_profile_url": c.get("author_href") or "",
                "post_url":            c.get("post_url") or "",
                "email":               ", ".join(emails),
                "post_snippet":        textwrap.shorten(c.get("post_text") or "", width=300, placeholder="…"),
            })
    print(f"[quick_test] Saved → {csv_path}")


asyncio.run(main())
