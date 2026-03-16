"""
storage.py — CSV read/write with deduplication for leads, posts, and run logs.

All writes are append-mode; existing data is never overwritten.
Dedup keys:
  leads.csv  → linkedin_profile_url (primary), email (fallback)
  posts.csv  → post_url
"""

import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEADS_CSV = OUTPUT_DIR / "leads.csv"
POSTS_CSV = OUTPUT_DIR / "posts.csv"
RUNS_LOG_CSV = OUTPUT_DIR / "runs_log.csv"
OUTREACH_CSV = OUTPUT_DIR / "outreach_drafts.csv"

# Column definitions
LEADS_COLS = [
    "email", "author_name", "author_title",
    "linkedin_profile_url", "post_url",
    "post_date", "run_id", "date_found",
]
POSTS_COLS = [
    "post_url", "author_name", "author_title",
    "linkedin_profile_url", "post_text",
    "has_email", "emails_found", "run_id", "scanned_at",
]
RUNS_COLS = [
    "run_id", "started_at", "completed_at",
    "searches_run", "posts_scanned", "leads_found", "status",
]
OUTREACH_COLS = [
    "email", "author_name", "subject", "body", "post_url", "generated_at",
]


def _load(path: Path, cols: list[str]) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, dtype=str).fillna("")
    return pd.DataFrame(columns=cols)


def _append(path: Path, new_rows: pd.DataFrame) -> int:
    """Append new_rows to CSV at path. Returns number of rows written."""
    if new_rows.empty:
        return 0
    write_header = not path.exists()
    new_rows.to_csv(path, mode="a", index=False, header=write_header)
    return len(new_rows)


# ── Leads ─────────────────────────────────────────────────────────────────────

def append_leads(posts: list, run_id: str) -> int:
    """
    Write new unique leads from a list of ScannedPost objects.
    A lead is one row per unique (profile_url or email).
    Returns count of new leads written.
    """
    existing = _load(LEADS_CSV, LEADS_COLS)
    existing_profiles = set(existing["linkedin_profile_url"].str.lower())
    existing_emails = set(existing["email"].str.lower())

    now = datetime.utcnow().isoformat()
    new_rows = []

    for post in posts:
        profile = post.linkedin_profile_url.lower()
        emails = post.emails or [""]  # at minimum one row per post with a profile URL

        for email in emails:
            email_low = email.lower()
            # Skip if we already have this profile or email
            if profile and profile in existing_profiles:
                continue
            if email_low and email_low in existing_emails:
                continue
            if not profile and not email_low:
                continue

            new_rows.append({
                "email": email,
                "author_name": post.author_name,
                "author_title": post.author_title,
                "linkedin_profile_url": post.linkedin_profile_url,
                "post_url": post.post_url,
                "post_date": "",
                "run_id": run_id,
                "date_found": now,
            })
            existing_profiles.add(profile)
            existing_emails.add(email_low)

    df = pd.DataFrame(new_rows, columns=LEADS_COLS)
    return _append(LEADS_CSV, df)


def append_leads_from_cards(cards: list[dict], run_id: str) -> int:
    """
    Write new unique leads from extracted_posts cards (dicts from search_runner).
    Deduped by linkedin_profile_url. Returns count of new leads written.
    """
    existing = _load(LEADS_CSV, LEADS_COLS)
    existing_profiles = set(existing["linkedin_profile_url"].str.lower())

    now = datetime.utcnow().isoformat()
    new_rows = []

    for card in cards:
        profile = (card.get("author_href") or "").lower().rstrip("/")
        if not profile:
            continue
        if profile in existing_profiles:
            continue

        emails = card.get("emails") or []
        new_rows.append({
            "email": ", ".join(emails),
            "author_name": card.get("author_name") or "",
            "author_title": card.get("author_title") or "",
            "linkedin_profile_url": card.get("author_href") or "",
            "post_url": card.get("post_url") or "",
            "post_date": "",
            "run_id": run_id,
            "date_found": now,
        })
        existing_profiles.add(profile)

    df = pd.DataFrame(new_rows, columns=LEADS_COLS)
    return _append(LEADS_CSV, df)


# ── Posts ─────────────────────────────────────────────────────────────────────

def append_posts(posts: list, run_id: str) -> int:
    """Write all scanned posts (deduped by post_url). Returns rows written."""
    existing = _load(POSTS_CSV, POSTS_COLS)
    existing_urls = set(existing["post_url"].str.lower())

    now = datetime.utcnow().isoformat()
    new_rows = []

    for post in posts:
        if post.post_url.lower() in existing_urls:
            continue
        new_rows.append({
            "post_url": post.post_url,
            "author_name": post.author_name,
            "author_title": post.author_title,
            "linkedin_profile_url": post.linkedin_profile_url,
            "post_text": post.post_text[:2000],  # cap text length
            "has_email": str(post.has_email),
            "emails_found": ",".join(post.emails),
            "run_id": run_id,
            "scanned_at": now,
        })
        existing_urls.add(post.post_url.lower())

    df = pd.DataFrame(new_rows, columns=POSTS_COLS)
    return _append(POSTS_CSV, df)


# ── Run log ───────────────────────────────────────────────────────────────────

def log_run(
    run_id: str,
    started_at: str,
    searches_run: int,
    posts_scanned: int,
    leads_found: int,
    status: str,
) -> None:
    row = pd.DataFrame([{
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": datetime.utcnow().isoformat(),
        "searches_run": searches_run,
        "posts_scanned": posts_scanned,
        "leads_found": leads_found,
        "status": status,
    }], columns=RUNS_COLS)
    _append(RUNS_LOG_CSV, row)


def load_runs() -> pd.DataFrame:
    return _load(RUNS_LOG_CSV, RUNS_COLS)


def load_leads() -> pd.DataFrame:
    return _load(LEADS_CSV, LEADS_COLS)


def load_posts() -> pd.DataFrame:
    return _load(POSTS_CSV, POSTS_COLS)


def new_run_id() -> str:
    return str(uuid.uuid4())[:8]


# ── Outreach drafts ───────────────────────────────────────────────────────────

def append_outreach(drafts: list[dict]) -> int:
    """Write outreach draft dicts to CSV. Returns rows written."""
    if not drafts:
        return 0
    df = pd.DataFrame(drafts, columns=OUTREACH_COLS)
    return _append(OUTREACH_CSV, df)


def load_outreach() -> pd.DataFrame:
    return _load(OUTREACH_CSV, OUTREACH_COLS)
