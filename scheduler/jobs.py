"""
jobs.py — APScheduler setup and the main scrape job definition.
"""

import asyncio
import json
import queue
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from data import storage
from outreach.generator import generate_drafts
from scraper.email_extractor import extract_emails
from scraper.search_runner import run_searches

CONFIG_FILE = Path(__file__).parent.parent / "config.json"

# Shared log queue — Flask SSE endpoint reads from this
log_queue: queue.Queue = queue.Queue()

_scheduler = BackgroundScheduler()


def _log(msg: str) -> None:
    print(msg)
    log_queue.put(msg)


def run_full_scrape() -> dict:
    """
    Main scrape job. Runs searches → scans posts → saves CSV → generates outreach.
    Returns a summary dict.
    """
    run_id = storage.new_run_id()
    started_at = datetime.utcnow().isoformat()
    _log(f"[run:{run_id}] Starting scrape at {started_at}")

    try:
        # ── 1. Search ──────────────────────────────────────────────────────
        _log("[run] Phase 1: Running searches...")
        search_result = asyncio.run(run_searches(log_fn=_log))
        cards = search_result.get("extracted_posts", [])
        searches_run = len(search_result["per_query"])
        _log(f"[run] Searches done. {len(cards)} posts extracted.")

        # ── 2. Enrich with email extraction ────────────────────────────────
        _log("[run] Phase 2: Extracting emails from post text...")
        for card in cards:
            card["emails"] = extract_emails(card.get("post_text", ""))
        emails_found = sum(1 for c in cards if c["emails"])
        _log(f"[run] Email extraction done. {emails_found} posts with email.")

        # ── 3. Save to CSV ─────────────────────────────────────────────────
        _log("[run] Phase 3: Saving results...")
        new_leads = storage.append_leads_from_cards(cards, run_id)
        _log(f"[run] Saved. {new_leads} new leads added.")

        # ── 4. Generate outreach drafts ────────────────────────────────────
        _log("[run] Phase 4: Generating outreach drafts...")
        leads_df = storage.load_leads()
        this_run_leads = leads_df[leads_df["run_id"] == run_id].to_dict("records")
        drafts = generate_drafts(this_run_leads)
        storage.append_outreach(drafts)
        _log(f"[run] {len(drafts)} outreach drafts generated.")

        # ── 5. Log run ─────────────────────────────────────────────────────
        storage.log_run(
            run_id=run_id,
            started_at=started_at,
            searches_run=searches_run,
            posts_scanned=len(cards),
            leads_found=new_leads,
            status="success",
        )
        _log(f"[run:{run_id}] Complete.")
        return {"status": "success", "run_id": run_id, "leads_found": new_leads}

    except Exception as e:
        _log(f"[run:{run_id}] FAILED: {e}")
        storage.log_run(
            run_id=run_id,
            started_at=started_at,
            searches_run=0,
            posts_scanned=0,
            leads_found=0,
            status="failed",
        )
        return {"status": "failed", "run_id": run_id, "error": str(e)}


def start_scheduler() -> None:
    """Start APScheduler with the cron from config.json."""
    config = json.loads(CONFIG_FILE.read_text())
    cron = config.get("schedule", "")
    if not cron:
        print("[scheduler] No schedule configured — manual runs only.")
        return

    parts = cron.strip().split()
    if len(parts) != 5:
        print(f"[scheduler] Invalid cron expression: {cron!r}")
        return

    minute, hour, dom, month, dow = parts
    _scheduler.remove_all_jobs()
    _scheduler.add_job(
        run_full_scrape,
        trigger="cron",
        minute=minute,
        hour=hour,
        day=dom,
        month=month,
        day_of_week=dow,
        id="linkedin_scrape",
        replace_existing=True,
    )
    if not _scheduler.running:
        _scheduler.start()
    job = _scheduler.get_job("linkedin_scrape")
    print(f"[scheduler] Scheduled. Next run: {job.next_run_time}")


def update_schedule(cron: str) -> str:
    """Update the scheduler cron and persist to config.json. Returns next run time."""
    config = json.loads(CONFIG_FILE.read_text())
    config["schedule"] = cron
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    start_scheduler()
    job = _scheduler.get_job("linkedin_scrape")
    return str(job.next_run_time) if job else "not scheduled"
