# LinkedIn Job Search Utility — Technical Architecture

**Version:** 1.0
**Stack:** Python 3.11+ · Playwright · Flask · APScheduler · pandas
**Last Updated:** 2026-03-09

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Flask Web App                         │
│   Config UI │ Run Trigger │ Results Table │ Downloads   │
└──────────────────────┬──────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │  Scheduler   │  (APScheduler — BackgroundScheduler)
                │  cron/manual │
                └──────┬──────┘
                       │
           ┌───────────▼───────────┐
           │     Scraper Engine     │
           │  ┌──────────────────┐  │
           │  │  Search Runner   │  │  ← Playwright (Chromium)
           │  └────────┬─────────┘  │
           │  ┌────────▼─────────┐  │
           │  │   Post Scanner   │  │  ← Playwright
           │  └────────┬─────────┘  │
           │  ┌────────▼─────────┐  │
           │  │ Email Extractor  │  │  ← regex
           │  └──────────────────┘  │
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │       Data Layer       │
           │  leads.csv             │
           │  posts.csv             │
           │  runs_log.csv          │
           │  outreach_drafts.csv   │
           └───────────┬───────────┘
                       │
           ┌───────────▼───────────┐
           │   Outreach Generator   │  ← Jinja2 templates
           │  (+ optional Claude API)│    or Anthropic API
           └───────────────────────┘
```

---

## Project File Structure

```
linkedin_util/
├── app.py                      # Flask entry point, registers blueprints
├── config.json                 # User config: queries, schedule, filters
├── .env                        # Secrets: LI_EMAIL, LI_PASSWORD, ANTHROPIC_API_KEY
├── requirements.txt
│
├── scraper/
│   ├── __init__.py
│   ├── browser.py              # Playwright setup, stealth config, login, cookie persistence
│   ├── search_runner.py        # Executes search queries, collects post URLs
│   ├── post_scanner.py         # Visits posts, extracts name/profile/text
│   └── email_extractor.py      # Regex patterns for email extraction + obfuscation handling
│
├── data/
│   ├── __init__.py
│   ├── storage.py              # CSV read/write with deduplication logic
│   └── output/                 # All generated CSVs land here
│       ├── leads.csv
│       ├── posts.csv
│       ├── runs_log.csv
│       └── outreach_drafts.csv
│
├── outreach/
│   ├── __init__.py
│   ├── generator.py            # Template-based or AI-based draft generation
│   └── templates/
│       └── email_template.txt  # Jinja2 email template
│
├── apply/                      # v2.0 — Easy Apply module (scaffolded)
│   ├── __init__.py
│   ├── easy_apply.py           # Detect + fill Easy Apply forms
│   ├── profile.py              # Stored applicant profile data (name, resume path, etc.)
│   └── tracker.py              # applications.csv read/write
│
├── scheduler/
│   ├── __init__.py
│   └── jobs.py                 # APScheduler setup and scrape job definition
│
└── web/
    ├── routes.py               # All Flask route handlers
    ├── static/
    │   ├── style.css
    │   └── run.js              # SSE client for live log streaming
    └── templates/
        ├── base.html           # Shared nav, layout
        ├── config.html         # Search query config form
        ├── run.html            # Manual run trigger + live log view
        ├── results.html        # Leads/posts table + download buttons
        └── history.html        # Past run stats
```

---

## Module Details

### `scraper/browser.py`

Responsibilities:
- Launch Playwright Chromium with stealth settings
- Load cookies from `session.json` if available
- Perform LinkedIn login if session is absent or expired
- Save cookies after successful login
- Expose a reusable `get_page()` context manager

Key implementation notes:
- Use `playwright-stealth` to mask automation fingerprint
- Set realistic `User-Agent` header (desktop Chrome/macOS)
- Disable `navigator.webdriver` flag via `init_script`

```python
# session.json structure
{
  "cookies": [...],   # Playwright cookie format
  "saved_at": "2026-03-09T12:00:00Z"
}
```

### `scraper/search_runner.py`

Responsibilities:
- Accept a list of search queries from `config.json`
- Navigate to `linkedin.com/search/results/content/?keywords={query}`
- Scroll page, collect post URLs (unique)
- Apply random delays between scroll events
- Return list of post URLs for the run

### `scraper/post_scanner.py`

Responsibilities:
- Visit each post URL
- Extract:
  - `author_name` — from post header `.update-components-actor__name`
  - `linkedin_profile_url` — href from author name anchor tag
  - `author_title` — subtitle below author name
  - `post_text` — full text content of the post body
- Pass `post_text` to `email_extractor.py`
- Return structured `Post` dataclass

### `scraper/email_extractor.py`

```python
import re

# Standard email pattern
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Obfuscated patterns: "name at gmail dot com"
OBFUSCATED_PATTERN = re.compile(
    r'(\w[\w.+\-]*)(?:\s+|\s*[\[\(]?\s*)(?:at|@)(?:\s*[\]\)]?\s*|\s+)'
    r'(\w[\w\-]*)(?:\s+|\s*[\[\(]?\s*)(?:dot|\.)(?:\s*[\]\)]?\s*|\s+)(\w+)',
    re.IGNORECASE
)

def extract_emails(text: str) -> list[str]:
    standard = EMAIL_PATTERN.findall(text)
    obfuscated = [
        f"{m[0]}@{m[1]}.{m[2]}"
        for m in OBFUSCATED_PATTERN.findall(text)
    ]
    return list(set(standard + obfuscated))
```

---

## Data Layer

### CSV Schemas

**`leads.csv`**
| Column | Type | Notes |
|--------|------|-------|
| `email` | string | May be empty if no email found |
| `author_name` | string | LinkedIn display name |
| `author_title` | string | Headline/job title |
| `linkedin_profile_url` | string | Primary dedup key |
| `post_url` | string | Source post |
| `post_date` | date | When post was published |
| `run_id` | string | UUID of the run that found this lead |
| `date_found` | datetime | When this row was written |

**`posts.csv`**
| Column | Type | Notes |
|--------|------|-------|
| `post_url` | string | Primary key |
| `author_name` | string | |
| `author_title` | string | |
| `linkedin_profile_url` | string | |
| `post_text` | string | Full post body |
| `has_email` | bool | True if email extracted |
| `emails_found` | string | Comma-separated list |
| `run_id` | string | |
| `scanned_at` | datetime | |

**`runs_log.csv`**
| Column | Type | Notes |
|--------|------|-------|
| `run_id` | string | UUID |
| `started_at` | datetime | |
| `completed_at` | datetime | |
| `searches_run` | int | |
| `posts_scanned` | int | |
| `leads_found` | int | New unique leads this run |
| `status` | string | `success`, `partial`, `failed` |

**`outreach_drafts.csv`**
| Column | Type | Notes |
|--------|------|-------|
| `email` | string | |
| `author_name` | string | |
| `subject` | string | |
| `body` | string | Full email body |
| `post_url` | string | Context source |
| `generated_at` | datetime | |

### Deduplication Logic (`data/storage.py`)

- On append, load existing CSV → check `linkedin_profile_url` (primary) or `email` (fallback)
- Only write rows where neither key already exists
- Use `pandas` for all CSV operations

---

## Web Dashboard (Flask)

### Routes

```
GET  /                      → redirect to /dashboard
GET  /dashboard             → leads table + run stats summary
GET  /config                → search config form
POST /config                → save to config.json, reschedule if cron changed
GET  /run                   → run control page
POST /run/start             → kick off scrape in background thread
GET  /run/logs              → SSE stream of live log lines
GET  /history               → past runs table from runs_log.csv
GET  /download/<filename>   → serve file from data/output/
```

### Live Log Streaming (SSE)

- Scraper writes log lines to a shared `queue.Queue`
- `/run/logs` route yields from the queue as `text/event-stream`
- `run.js` on the client connects via `EventSource` and appends lines to a `<pre>` element

---

## Scheduler (`scheduler/jobs.py`)

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def start_scheduler(cron_expression: str):
    scheduler.remove_all_jobs()
    minute, hour, dom, month, dow = cron_expression.split()
    scheduler.add_job(
        run_full_scrape,
        trigger='cron',
        minute=minute, hour=hour,
        day=dom, month=month, day_of_week=dow,
        id='linkedin_scrape'
    )
    if not scheduler.running:
        scheduler.start()
```

Config in `config.json`:
```json
{
  "queries": ["hiring QA engineer remote", "SDET opentowork Bay Area"],
  "max_posts_per_run": 100,
  "schedule": "0 8 * * 1",
  "location": "San Francisco Bay Area"
}
```

---

## Anti-Detection Strategy

| Technique | Implementation |
|-----------|---------------|
| Stealth mode | `playwright-stealth` library, removes `webdriver` flag |
| Human-like delays | `random.gauss(3.0, 1.0)` seconds between actions (min 1.5s) |
| Scroll randomization | Random scroll distance + pause before each scroll |
| User-agent | Realistic macOS Chrome UA, rotated per run |
| Session reuse | Cookies persisted to avoid repeated logins |
| Run caps | Max 100 posts per run by default (configurable) |

---

## Dependencies

```
# requirements.txt
playwright>=1.40
playwright-stealth>=1.0
flask>=3.0
apscheduler>=3.10
pandas>=2.1
jinja2>=3.1
python-dotenv>=1.0
anthropic>=0.23      # optional — for AI outreach drafts
```

Install:
```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Risk & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LinkedIn detects automation | Medium | Stealth mode + delays + session reuse |
| Session expires mid-run | Low | Auto re-login with stored credentials |
| Email false positives | Medium | Regex validation + TLD allowlist |
| Posts without public contact | High (normal) | Log + skip; still save as lead via profile URL |
| Data loss on crash | Low | Append-write after each post (not batch) |
| IP rate limit | Medium | Cap posts/run; add inter-run cooldown |

---

## Build Sequence

Build in this order — each step is independently testable:

1. **`scraper/browser.py`** — Login + cookie save/load. Test: verify `session.json` created and LinkedIn home loads without re-login.
2. **`scraper/search_runner.py`** — Run 2 test queries, print collected post URLs.
3. **`scraper/post_scanner.py` + `email_extractor.py`** — Scan 10 posts, print extracted name/profile/email.
4. **`data/storage.py`** — Write to CSVs, verify deduplication on second write.
5. **`app.py` + `web/`** — Flask app loads at `localhost:5000`, results table renders.
6. **`scheduler/jobs.py`** — Scheduler fires on configured cron, run appears in history.
7. **`outreach/generator.py`** — `outreach_drafts.csv` generated with correct template substitution.
8. *(v2)* **`apply/easy_apply.py`** — Detects Easy Apply button, fills form in test mode.
9. *(v2)* **`apply/tracker.py`** + "Applications" dashboard tab.

---

## v2.0 Easy Apply Module (Scaffolded)

```
apply/
├── profile.py      # Applicant data: name, email, phone, resume path, cover letter
├── easy_apply.py   # Playwright: detect button → fill form → screenshot → submit
└── tracker.py      # applications.csv: job URL, company, title, status, date
```

`applications.csv` schema:
| job_url | company | job_title | applied_at | status | notes |

Status lifecycle: `Applied → Viewed → Responded → Interview → Rejected`
