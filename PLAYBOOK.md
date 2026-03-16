# Job Search Playbook — Swapnil Tilaye

Personal guide for using the LinkedIn Utility to find Staff/Principal SDET roles.

---

## Your Profile at a Glance

| | |
|--|--|
| **Name** | Swapnil Tilaye |
| **Current** | QA Engineer, Amazon (Sunnyvale) |
| **Experience** | 10+ years — Amazon, F5 Networks, EdgeQ, DISH Technology |
| **Core Stack** | Python, Pytest, Playwright, Robot Framework, Selenium |
| **Differentiators** | 10+ US Patents · MCP/AI agent frameworks · 5G/IoT/Bluetooth · MS CS GPA 3.8 |
| **Target Level** | Staff / Principal / Senior SDET or Test Automation Engineer |
| **Target Location** | Remote preferred · Bay Area open |
| **Contact** | swapniltilaye@gmail.com · 970-389-4011 · linkedin.com/in/swapniltilaye |

---

## Search Queries (already in `config.json`)

12 queries tuned to your exact background:

| Query | Why It Targets You |
|-------|--------------------|
| `hiring Staff SDET remote Python` | Matches your seniority + core language |
| `hiring Staff QA Engineer Bay Area` | Local hiring managers posting direct |
| `hiring Senior SDET Pytest Playwright` | Your exact tools — F5 + Amazon |
| `Staff Test Automation Engineer Python remote` | Staff-level remote roles |
| `Principal QA Engineer hiring` | Next-level stretch roles |
| `hiring SDET AI automation engineer` | Targets your MCP/AI agent work |
| `opentowork SDET Staff hiring manager` | Hiring managers reaching out to candidates |
| `hiring QA engineer Python pytest remote 2026` | Fresh 2026 postings |
| `Staff engineer test automation Kubernetes hiring` | Platform SDET — matches F5 + EdgeQ |
| `hiring automation engineer AI agent MCP` | Rare skill — almost no competition |
| `Senior SDET IoT embedded systems hiring` | Amazon Bluetooth + EdgeQ 5G combo |
| `Principal SDET platform automation hiring` | Principal-track roles |

**Schedule:** Mon / Wed / Fri at 8am (configured in `config.json` as `"0 8 * * 1,3,5"`)

---

## Outreach Message (auto-generated into `outreach_drafts.csv`)

```
Subject: Staff SDET @ Amazon — open to [Role] roles

Hi [Name],

[Post context — auto-filled from their post]

I'm Swapnil — Staff SDET at Amazon with 10+ years across Amazon, F5 Networks,
and EdgeQ. I specialize in Python test automation (Pytest, Playwright, Robot FW),
CI/CD pipelines, and AI/agentic frameworks using MCP. I hold 10+ US patents and
am actively exploring Staff/Principal SDET opportunities (remote preferred, Bay Area open).

Would love to connect if there's a fit or referral opportunity.

Swapnil Tilaye
linkedin.com/in/swapniltilaye | swapniltilaye@gmail.com | 970-389-4011
```

> Edit `outreach/templates/email_template.txt` to adjust tone or content.

---

## Weekly Workflow

```
Monday 8am  ─── Auto-run fires (search + scan + extract)
                       ↓
              leads.csv updated
              outreach_drafts.csv updated
                       ↓
Monday evening ── Open http://localhost:5000/dashboard
                       ↓
              Review new leads table
                       ↓
         ┌─────────────┴──────────────┐
    Has email?                    No email?
         │                            │
Copy draft from               Click LinkedIn profile
outreach_drafts.csv           URL → send LinkedIn DM
Paste into Gmail              using the post as context
         │                            │
         └─────────────┬──────────────┘
                       ↓
              Log status manually
              (or wait for v2 tracker)

Wednesday 8am ─── Repeat
Friday 8am    ─── Repeat
```

---

## Your Strongest Targeting Angles

### 1. MCP / AI Agent Experience (rarest signal)
Almost no SDET resumes mention MCP or agentic frameworks in 2026.
Query: `"hiring automation engineer AI agent MCP"`
What to say: *"I built agentic automation frameworks using MCP servers with multi-agent architecture at both Amazon and Mimic."*

### 2. Patents (conversation starter)
10+ US patents from DISH Technology sets you apart from all other QA candidates.
What to say: *"I hold 10+ US patents in systems engineering, which reflects the depth I bring to quality architecture."*

### 3. Full-Stack SDET (hardware to cloud)
You have Bluetooth/IoT (Amazon), 5G core/telecom (EdgeQ), distributed systems (F5), and consumer credit (Experian).
Few SDETs span hardware, networking, and cloud. Lead with this for platform/infra SDET roles.

### 4. AI/ML QA (emerging niche)
Your Mimic role (AI-driven malware defense + LLM agents) positions you for AI company SDET roles.
Target: OpenAI, Anthropic, Scale AI, Cohere, Mistral — search `"SDET AI ML hiring"`.

---

## Target Company Tiers

### Tier 1 — Best fit for your stack
| Company | Why |
|---------|-----|
| Apple | QA for hardware + software (Xcode, devices) — matches Amazon IoT work |
| Google | Platform SDET, Pytest/Playwright heavy — matches F5 + Amazon |
| Meta | Infrastructure test automation at scale |
| Netflix | Senior/Staff SDET, Python-first culture |
| Uber / Lyft | Platform SDET, distributed systems — matches F5 |

### Tier 2 — Strong match
| Company | Why |
|---------|-----|
| OpenAI / Anthropic | AI product QA — your MCP + LLM agent background is rare here |
| Qualcomm / Broadcom | Embedded + network testing — matches EdgeQ 5G work |
| Palo Alto Networks | Security QA — matches Mimic ransomware defense work |
| Cisco / Juniper | Network automation — matches F5 + EdgeQ |
| Databricks / Snowflake | Data platform SDET |

### Tier 3 — Add to searches
| Company | Why |
|---------|-----|
| Scale AI | AI data quality QA |
| Stripe / Block | Payments backend QA — matches Experian |
| Cloudflare | Network/edge QA — matches F5 |

---

## LinkedIn DM Template (for leads without email)

Use this when the tool finds a profile URL but no email:

```
Hi [Name],

I came across your post about [role/topic] and wanted to reach out.

I'm Swapnil, a Staff SDET currently at Amazon (Bluetooth/IoT automation) with
prior experience at F5 Networks and EdgeQ (5G). I hold 10+ US patents and specialize
in Python-based automation frameworks, CI/CD, and AI agentic tooling.

Open to Staff/Principal SDET roles — remote preferred. Would love to connect
if there's a fit or you know of any openings on your team.

Thanks!
```

---

## Tips for Best Results

**Do:**
- Run the tool Mon/Wed/Fri (already scheduled) — consistent but not aggressive
- Follow up on leads within 24 hours while the post is still fresh
- Mention the specific post in your message — shows you actually read it
- For high-value targets (Apple, Google, Meta) — send LinkedIn DM *and* email if both are available

**Don't:**
- Change `max_posts_per_run` above 200 — risks LinkedIn flagging the account
- Run more than once per day — the scheduler handles spacing
- Send identical messages — the template auto-personalizes with post context

---

## Quick Start Checklist

- [ ] `cp .env.example .env` and set `CHROME_PROFILE=true`
- [ ] Quit Chrome completely
- [ ] `python app.py`
- [ ] Open http://localhost:5000/config — verify 12 queries are there
- [ ] Click **Run** → **Start Run** — watch live logs
- [ ] After run: check **Results** tab for new leads
- [ ] Download `outreach_drafts.csv` → paste top drafts into Gmail
- [ ] Schedule is already set — next auto-run: Monday 8am

---

## Files to Know

| File | What to do with it |
|------|--------------------|
| `config.json` | Tune queries as you learn what works |
| `outreach/templates/email_template.txt` | Tweak the message voice |
| `data/output/leads.csv` | Your master lead list |
| `data/output/outreach_drafts.csv` | Copy-paste into Gmail |
| `data/output/runs_log.csv` | Track which runs found the most leads |
