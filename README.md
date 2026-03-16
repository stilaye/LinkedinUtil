# LinkedIn Job Search Utility

Automated LinkedIn post scanner that finds recruiter contact info at scale.
Inspired by Oscar Leung's job-search automation project.

**What it does:**
- Runs configurable keyword searches on LinkedIn
- Scans post results and extracts: author name, LinkedIn profile URL, email
- Deduplicates leads across runs and exports to CSV
- Generates personalized outreach email drafts
- Web dashboard to configure, trigger, and review results
- Optional recurring schedule (daily/weekly via cron)

---

## Prerequisites

- Python 3.11+
- A LinkedIn account (personal — not a company page)
- pip
- Google Chrome installed (required for Chrome Profile auth mode)

---

## Setup

### 1. Clone / navigate to the project

```bash
cd /Users/avyaan/LinkedinUtil
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browser

```bash
playwright install chromium
```

> If you're using **Chrome Profile mode** (Option 1), also make sure Google Chrome is installed
> on your system. The tool uses your real Chrome installation via `channel="chrome"` — the
> Playwright Chromium install above is only used as a fallback.

### 4. Configure credentials

```bash
cp .env.example .env
```

There are **three auth modes** — pick one:

---

**Option 1 — Chrome Profile (recommended)**
Reuses your already-logged-in Chrome session. No password needed.

```
CHROME_PROFILE=true
```

> Quit Chrome completely before running the tool. The scraper copies your `Default` Chrome profile to a temp directory and runs headlessly from it.
> If your Chrome profile is in a non-standard location, also set:
> `CHROME_PROFILE_DIR=/path/to/your/Chrome/profile`

---

**Option 2 — Saved cookie session**
After your first credential login (Option 3), a `session.json` is saved automatically. On subsequent runs the saved cookies are reused — no extra config needed.

---

**Option 3 — Email + password**
Fallback when neither of the above is configured.

```
LI_EMAIL=your@email.com
LI_PASSWORD=yourpassword
```

---

**Optional — Claude API for AI outreach drafts**

```
ANTHROPIC_API_KEY=sk-ant-...
```

Only needed if `use_ai_outreach=true` in `config.json`.

> **Security:** `.env` is never committed to git. Keep it local.

### 5. Configure search queries

Edit `config.json`:

```json
{
  "queries": [
    "hiring Staff SDET remote Python",
    "hiring Staff QA Engineer Bay Area",
    "hiring Senior SDET Pytest Playwright"
  ],
  "location": "San Francisco Bay Area",
  "date_filter": "past-week",
  "geo_urns": ["103644278"],
  "max_posts_per_run": 150,
  "schedule": "0 8 * * 1,3,5",
  "use_ai_outreach": false
}
```

#### All Config Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `queries` | `list[str]` | LinkedIn keyword search terms. One search per entry. Be specific — include seniority, skills, location keywords. |
| `location` | `string` | Human-readable label. Not used in search URLs — use `geo_urns` for actual filtering. |
| `date_filter` | `string` | Filter posts by recency. Options: `"past-24h"`, `"past-week"`, `"past-month"`, `"none"`. Default: `""` (no filter). |
| `geo_urns` | `list[str]` | LinkedIn geo URN IDs for country/region filtering. See table below. Leave `[]` for no geo filter. |
| `max_posts_per_run` | `int` | Max total posts extracted across all queries per run. Split evenly across queries. Default: `100`. Keep ≤ 200. |
| `schedule` | `string` | Cron expression for automatic scheduled runs. Leave `""` to disable scheduling. |
| `use_ai_outreach` | `bool` | `true` — use Claude API (requires `ANTHROPIC_API_KEY`) for personalized drafts. `false` — use template. |

#### `date_filter` Options

| Value | Meaning |
|-------|---------|
| `"past-24h"` | Posts from the last 24 hours |
| `"past-week"` | Posts from the last 7 days |
| `"past-month"` | Posts from the last 30 days |
| `"none"` or `""` | No date filter (all-time) |

#### `geo_urns` — Common Country Codes

| Country | URN |
|---------|-----|
| United States | `"103644278"` |
| United Kingdom | `"101165590"` |
| Canada | `"101174742"` |
| Australia | `"101452733"` |
| India | `"102713980"` |
| Germany | `"101282230"` |
| Singapore | `"102454443"` |

You can combine multiple countries:
```json
"geo_urns": ["103644278", "101174742"]
```
Leave empty for worldwide results:
```json
"geo_urns": []
```

### 6. Launch

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Example: What the Tool Extracts

Here's a real-world example of what the tool finds and generates.

### Input — LinkedIn post found during a search

> A Software Engineering Manager at Apple posts about hiring a **Quality & Test Automation Engineer**
> for the Xcode Instruments & Memory Tools team. The post includes their name, title, and a job application link.

### Output 1 — Row written to `leads.csv`

| Field | Value |
|-------|-------|
| `author_name` | Kacper Harasim |
| `author_title` | Software Engineering Manager at Apple |
| `linkedin_profile_url` | https://linkedin.com/in/kacper-harasim |
| `email` | *(empty — no email in post body)* |
| `post_url` | https://linkedin.com/posts/kacper-harasim_... |
| `date_found` | 2026-03-10T08:14:22 |

> **Note:** Even when no email is present, the tool still saves the lead with the poster's
> name and LinkedIn profile URL so you can reach out directly via LinkedIn message.

### Output 2 — Row written to `outreach_drafts.csv`

For leads **with an email**, the tool auto-generates a ready-to-send draft (~300 characters):

```
Subject: Quick note — Kacper

Hi Kacper,

I came across your post about the QA & Test Automation role on the Xcode team.
I'm actively looking for SDET / Test Automation roles and would love to connect
if there's a fit. Happy to share my resume or chat briefly — whatever works best.

[Your Name]
```

> Drafts are saved to `outreach_drafts.csv`. Copy-paste directly into Gmail — nothing is sent automatically.

### What happens when there's no email?

Posts like this one (job link only, no email) still produce a **lead row** with the poster's
LinkedIn profile URL. Your next step: visit their profile and send a LinkedIn message directly.
The tool gives you everything you need — name, title, and the source post for context.

---

## Dashboard Walkthrough

### Results (`/dashboard`)
- Stats: total leads, leads with email, total runs
- Table: every unique lead with name, title, email, profile link, source post
- Download buttons for all CSVs

### Run (`/run`)
- Click **Start Run** to trigger an immediate scrape
- Live log streams in real-time as the scraper works
- Run completes automatically — no need to keep the page open

### Config (`/config`)
- Edit search queries (one per line)
- Set max posts per run
- Set or change the recurring schedule
- Toggle AI outreach drafts

### History (`/history`)
- Table of all past runs with stats and status

---

## Running Manually (CLI)

#### One-time session setup (first time only)
```bash
python setup_session.py
```
Opens a headed browser window. Log in with **email + password** (not "Continue with Google"). Once you see your LinkedIn feed, press Enter. Session is saved to `session.json`.

#### Quick search test
```bash
# Default query from config.json
python quick_test.py

# Custom query
python quick_test.py "hiring Staff SDET remote Python"
```
Runs a search, prints results to terminal, and saves a timestamped CSV to `data/output/leads_YYYYMMDD_HHMMSS.csv`.

#### Test individual modules
```bash
# Test login + session
python -m scraper.browser

# Test search
python -m scraper.search_runner
```

---

## Output Files

All outputs are written to `data/output/`:

| File | Contents |
|------|----------|
| `leads.csv` | Unique leads: email, name, title, LinkedIn profile URL, post URL |
| `posts.csv` | Every scanned post with full metadata |
| `runs_log.csv` | Per-run stats: searches run, posts scanned, new leads, status |
| `outreach_drafts.csv` | Personalized email drafts ready to send |

Runs **append** to existing files — no data is ever overwritten. Deduplication is automatic.

---

## Scheduling

Set a cron expression in `config.json` or the Config page.

Common schedules:

| Cron | Meaning |
|------|---------|
| `0 8 * * 1` | Every Monday at 8am |
| `0 9 * * 1-5` | Weekdays at 9am |
| `0 8 * * *` | Every day at 8am |

The scheduler starts automatically when you run `python app.py`.
No restart needed after changing the schedule in the dashboard.

---

## Outreach Drafts

Drafts are generated automatically after each run and saved to `outreach_drafts.csv`.

**Template mode (default):** Uses `outreach/templates/email_template.txt` with Jinja2 substitution.
Edit the template to match your voice and target role.

**AI mode:** Set `use_ai_outreach: true` in `config.json` and add `ANTHROPIC_API_KEY` to `.env`.
Uses Claude Haiku to write a personalized draft for each lead with an email address.

> Drafts are copy-paste ready for Gmail. The tool never sends emails automatically.

---

## Anti-Detection Notes

The scraper uses several techniques to avoid LinkedIn bot detection:

- **Chrome Profile mode** — uses your real Chrome profile and cookies, making the session indistinguishable from a normal human login (best option)
- **Playwright stealth** — removes `navigator.webdriver` fingerprint on all modes
- **Random delays** — 1.5–4.5 seconds between actions (normally distributed)
- **Session reuse** — cookies saved to `session.json` after first credential login, avoiding repeated logins
- **Run caps** — max 100 posts per run by default; increase carefully

**Recommended limits:**
- Keep `max_posts_per_run` ≤ 200
- Don't run more than once per day
- Chrome Profile mode is the least likely to trigger bot detection — use it if you can

---

## Project Structure

```
LinkedinUtil/
├── app.py                      # Flask entry point
├── config.json                 # Search queries and schedule
├── .env                        # Credentials (never commit this)
├── .env.example                # Template for .env
├── requirements.txt
│
├── scraper/
│   ├── browser.py              # Playwright setup, login, cookie persistence
│   ├── search_runner.py        # Runs search queries, collects post URLs
│   ├── post_scanner.py         # Extracts name / profile URL / post text
│   └── email_extractor.py      # Regex email extraction
│
├── data/
│   ├── storage.py              # CSV read/write with deduplication
│   └── output/                 # Generated CSVs (gitignored)
│
├── outreach/
│   ├── generator.py            # Template or AI email draft generation
│   └── templates/
│       └── email_template.txt  # Editable outreach template
│
├── scheduler/
│   └── jobs.py                 # APScheduler + full scrape job
│
└── web/
    ├── routes.py               # Flask routes
    ├── static/                 # CSS + JS
    └── templates/              # HTML pages
```

---

## Troubleshooting

**Chrome Profile mode: "LinkedIn is not logged in"**
Open Chrome, log in to LinkedIn, then quit Chrome completely and re-run the tool.

**Chrome Profile mode: "Default profile not found"**
Your Chrome profile may be in a non-default location. Find it via `chrome://version` → "Profile Path", then set `CHROME_PROFILE_DIR` in `.env` to the parent folder (not the profile folder itself).

**Chrome Profile mode: profile copy errors / lock files**
Chrome must be fully closed before running. On macOS, `Cmd+Q` — don't just close the window. Check Activity Monitor to confirm no `Google Chrome` processes are running.

**Login fails / CAPTCHA detected (credential mode)**
Log in to LinkedIn manually in Chrome. Delete `session.json` if it exists, then re-run. Consider switching to Chrome Profile mode to avoid this entirely.

**No posts found for a query**
LinkedIn search URLs change periodically. Check `scraper/search_runner.py` — update the `SEARCH_URL` template if needed.

**Post data (name, email) not extracting**
LinkedIn's CSS selectors change frequently. Update `_SELECTORS` in `scraper/post_scanner.py` by inspecting the page in Chrome DevTools.

**Dashboard not loading**
Make sure you're running `python app.py` from the `LinkedinUtil/` directory, not a subdirectory.

**APScheduler warnings on startup**
Normal on first run. The scheduler initializes cleanly once a cron is set.

---

## Roadmap

- **v2.0 — Easy Apply automation:** auto-detect Easy Apply jobs, fill and submit applications, track status in `applications.csv`
- **v2.0 — Application dashboard:** track Applied → Responded → Interview → Rejected per job

---

## Disclaimer

This tool is for personal job search use. Web scraping LinkedIn may be against their Terms of Service. Use responsibly and at your own risk. Do not use for spam, mass outreach, or commercial purposes.
