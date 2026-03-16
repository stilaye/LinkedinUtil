# LinkedIn Job Search Utility — Product Spec

**Version:** 1.0
**Owner:** Solo builder
**Stack:** Python + Playwright + Flask
**Last Updated:** 2026-03-09

---

## Problem

Manual LinkedIn job searching is slow, inconsistent, and doesn't scale. Searching across dozens of keyword combinations, scanning posts for recruiter emails, and tracking leads takes hours of repeated effort with no reliable output format.

---

## Solution

An automated tool that:

1. Runs configurable LinkedIn searches on demand or on a schedule
2. Scans posts and extracts: **author name, LinkedIn profile URL, email**
3. Deduplicates and exports leads to CSV (keyed on profile URL or email)
4. Drafts personalized outreach emails for each lead
5. Provides a simple web dashboard to configure, trigger, and review results

---

## Features (v1.0)

### F1 — Search Engine
- Configure multiple search queries (keywords, location, job type filters)
- Execute all searches sequentially with human-like delays
- Collect post URLs from search results pages
- Track success/failure per search run
- Configurable max posts per run (default: 100)

### F2 — Post Scanner
- Visit each collected post URL
- Extract per post:
  - Author **name** (display name)
  - Author **LinkedIn profile URL** (e.g., `linkedin.com/in/oscar-leung`)
  - Author headline / title
  - Full post text
- Apply regex to find **emails** in post body and comments
- Flag posts containing contact info

### F3 — Lead Export
- Deduplicate leads (keyed on email OR LinkedIn profile URL)
- Export two CSVs:
  - `leads.csv` — email, author name, LinkedIn profile URL, post URL, date found
  - `posts.csv` — all scanned posts with full metadata
- Append mode: new runs add to existing CSVs without overwriting
- Posts without email still generate a lead row (profile URL + name only)

### F4 — Outreach Draft Generator
- For each unique lead, generate a personalized draft email
- Uses Jinja2 templates with variable substitution (name, role, post context)
- Exports to `outreach_drafts.csv` — ready to copy-paste into Gmail
- Optional: Claude API integration for AI-personalized drafts

### F5 — Web Dashboard
- **Config page:** set search queries, location filters, schedule
- **Run page:** trigger manual run, view live log stream (SSE)
- **Results page:** sortable table of leads, posts, outreach drafts
- **Download buttons:** export all CSVs
- **History page:** past run stats (searches run, posts scanned, leads found)

### F6 — Scheduler
- Configure recurring runs (daily, weekly, or custom cron expression)
- Runs execute in background, results appended to CSVs automatically
- Dashboard shows next scheduled run time and last run summary

---

## Out of Scope (v1.0)

- Auto-sending emails (user sends manually from drafts)
- LinkedIn API (scraping only)
- Multi-user / cloud hosting
- Easy Apply automation (→ v2.0)

---

## Roadmap: v2.0 — Easy Apply Automation

### F7 — Easy Apply Bot
- Detect "Easy Apply" button on job listings (vs. external apply redirect)
- Auto-fill LinkedIn Easy Apply form fields using stored profile data:
  - Name, email, phone, resume upload, cover letter text
- Configurable per-run limits: max applications, job type filters, salary floor
- **Human-in-the-loop mode:** screenshot each form before submitting for user review
- Track applications in `applications.csv` (job title, company, URL, status, date)
- Skip already-applied jobs (dedup by job URL)

### F8 — Application Dashboard Extension
- New dashboard tab: "Applications" — table of all submitted applications
- Status tracking: `Applied → Viewed → Responded → Interview → Rejected`
- Manual status updates via dashboard UI

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Search success rate | ≥ 95% (< 5% failures per run) |
| Email false positive rate | < 10% |
| Dashboard availability | No crashes during normal use |
| Full run time (100 posts) | < 60 minutes |
| Lead deduplication | 0 duplicate emails or profile URLs across runs |
