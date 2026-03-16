"""
browser.py — Playwright browser setup, stealth config, LinkedIn login, session persistence.

Three auth modes (set in .env):
  1. CHROME_PROFILE=true   — reuse your existing logged-in Chrome profile (recommended)
  2. session.json present  — reuse a previously saved cookie session
  3. LI_EMAIL + LI_PASSWORD — full credential login (fallback)

Usage (standalone test):
    python -m scraper.browser
"""

import json
import os
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, BrowserContext, Page
from playwright_stealth import Stealth

_stealth = Stealth()

load_dotenv()

SESSION_FILE = Path(__file__).parent.parent / "session.json"
LI_LOGIN_URL = "https://www.linkedin.com/login"
LI_FEED_URL = "https://www.linkedin.com/feed/"

SESSION_MAX_AGE_HOURS = 12

# Default Chrome user data directory on macOS
_DEFAULT_CHROME_PROFILE = Path.home() / "Library/Application Support/Google/Chrome"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


def _human_delay(min_s: float = 1.5, max_s: float = 4.5) -> None:
    """Sleep for a normally-distributed random duration."""
    delay = max(min_s, random.gauss((min_s + max_s) / 2, (max_s - min_s) / 4))
    time.sleep(min(delay, max_s))


def _load_session() -> dict | None:
    """Return saved cookie session if it exists and is not stale."""
    if not SESSION_FILE.exists():
        return None
    try:
        data = json.loads(SESSION_FILE.read_text())
        saved_at = datetime.fromisoformat(data["saved_at"])
        if datetime.utcnow() - saved_at > timedelta(hours=SESSION_MAX_AGE_HOURS):
            print("[browser] Session is stale — will re-login.")
            return None
        return data
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


def _save_session(cookies: list) -> None:
    """Persist cookies to session.json for future runs."""
    SESSION_FILE.write_text(json.dumps({
        "cookies": cookies,
        "saved_at": datetime.utcnow().isoformat(),
    }, indent=2))
    print(f"[browser] Session saved → {SESSION_FILE}")


async def _is_logged_in(page: Page) -> bool:
    """Navigate to the feed and check if we're actually logged in."""
    try:
        await page.goto(LI_FEED_URL, wait_until="domcontentloaded", timeout=15_000)
        url = page.url
        # Must land on /feed/ itself — not the login page with feed in the redirect param
        return url.startswith("https://www.linkedin.com/feed")
    except Exception:
        return False


async def _login(page: Page) -> None:
    """Perform full credential login."""
    email = os.getenv("LI_EMAIL")
    password = os.getenv("LI_PASSWORD")
    if not email or not password:
        raise EnvironmentError(
            "Set LI_EMAIL and LI_PASSWORD in .env, "
            "or use CHROME_PROFILE=true to reuse your Chrome session."
        )

    print("[browser] Logging in with credentials...")
    await page.goto(LI_LOGIN_URL, wait_until="domcontentloaded")
    _human_delay(1.0, 2.5)
    await page.fill("#username", email)
    _human_delay(0.5, 1.5)
    await page.fill("#password", password)
    _human_delay(0.5, 1.5)
    await page.click('[type="submit"]')
    await page.wait_for_url(lambda url: "login" not in url, timeout=30_000)
    _human_delay(2.0, 3.5)

    if "checkpoint" in page.url or "challenge" in page.url:
        raise RuntimeError(
            "LinkedIn security checkpoint detected. "
            "Log in manually in Chrome once to clear it, then re-run."
        )
    print(f"[browser] Login successful → {page.url}")


# ── Chrome profile mode ───────────────────────────────────────────────────────

def _get_chrome_profile_dir() -> Path:
    """
    Return the Chrome user data directory.
    Override with CHROME_PROFILE_DIR in .env; otherwise uses the macOS default.
    """
    custom = os.getenv("CHROME_PROFILE_DIR")
    if custom:
        return Path(custom)
    return _DEFAULT_CHROME_PROFILE


def _find_linkedin_profile() -> tuple[Path, str]:
    """
    Auto-detect which Chrome profile has LinkedIn's li_at auth cookie.
    Returns (profile_dir, profile_name).
    Raises RuntimeError if none found.
    """
    import browser_cookie3

    profile_dir = _get_chrome_profile_dir()

    # Candidate profile folder names
    candidates = ["Default"] + [d.name for d in sorted(profile_dir.iterdir())
                                 if d.is_dir() and d.name.startswith("Profile ")]

    for name in candidates:
        cookie_file = profile_dir / name / "Cookies"
        if not cookie_file.exists():
            continue
        try:
            cookies = list(browser_cookie3.chrome(
                domain_name='.linkedin.com', cookie_file=str(cookie_file)
            ))
            if any(c.name == "li_at" for c in cookies):
                print(f"[browser] Auto-detected LinkedIn profile: '{name}'")
                return profile_dir, name
        except Exception:
            continue

    raise RuntimeError(
        "No Chrome profile found with LinkedIn logged in. "
        "Open Chrome, log in to LinkedIn, then re-run."
    )


def _read_chrome_cookies() -> list[dict]:
    """
    Read and decrypt LinkedIn cookies from the auto-detected Chrome profile.
    Uses browser_cookie3 which handles macOS Keychain decryption.
    Chrome can be open or closed — no profile copy needed.
    """
    import browser_cookie3

    profile_dir, profile_name = _find_linkedin_profile()
    cookie_file = str(profile_dir / profile_name / "Cookies")

    raw = list(browser_cookie3.chrome(domain_name='.linkedin.com', cookie_file=cookie_file))

    # Convert http.cookiejar.Cookie → Playwright cookie format
    pw_cookies = []
    for c in raw:
        domain = c.domain if c.domain.startswith('.') else f'.{c.domain}'
        entry: dict = {
            "name": c.name,
            "value": c.value,
            "domain": domain,
            "path": c.path or "/",
            "secure": bool(c.secure),
        }
        if c.expires and c.expires > 0:
            entry["expires"] = float(c.expires)
        pw_cookies.append(entry)

    print(f"[browser] Chrome cookies loaded: {len(pw_cookies)} cookies from profile '{profile_name}'")
    return pw_cookies


@asynccontextmanager
async def _chrome_profile_context(pw):
    """
    Launch Playwright by injecting cookies read from the Chrome profile.
    Auto-detects which profile has LinkedIn logged in.
    No profile copy needed. Chrome can be open or closed.

    Requirements:
    - Set CHROME_PROFILE=true in .env
    - LinkedIn must be logged in in at least one Chrome profile
    """
    cookies = _read_chrome_cookies()

    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    user_agent = random.choice(USER_AGENTS)
    context: BrowserContext = await browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1280, "height": 800},
        locale="en-US",
        timezone_id="America/Los_Angeles",
    )
    await _stealth.apply_stealth_async(context)
    await context.add_cookies(cookies)
    page = await context.new_page()

    if not await _is_logged_in(page):
        raise RuntimeError(
            "Chrome profile mode: cookies injected but LinkedIn session is invalid. "
            "Log into LinkedIn in Chrome again to refresh the session."
        )
    print("[browser] Chrome profile mode: LinkedIn session active.")

    try:
        yield context, page
    finally:
        await browser.close()


# ── Main context manager ──────────────────────────────────────────────────────

def _make_headless_browser_context(pw):
    """Shared helper: launch headless Chromium + stealth context."""
    return pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )


@asynccontextmanager
async def get_browser_context():
    """
    Yields a ready-to-use (logged-in) (BrowserContext, Page) pair.

    Auth priority:
      1. LI_AT in .env          → paste your li_at cookie value (no popups, recommended)
      2. Valid session.json      → reuse saved cookies from a previous run
      3. LI_EMAIL + LI_PASSWORD  → full credential login
      4. CHROME_PROFILE=true     → read cookies from Chrome (triggers Keychain popup)
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        user_agent = random.choice(USER_AGENTS)
        context: BrowserContext = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )
        await _stealth.apply_stealth_async(context)
        page = await context.new_page()

        # ── Mode 1: LI_AT cookie value from .env ─────────────────────────
        li_at = os.getenv("LI_AT", "").strip()
        if li_at:
            print("[browser] Using LI_AT cookie from .env ...")
            await context.add_cookies([{
                "name": "li_at",
                "value": li_at,
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
            }])
            if await _is_logged_in(page):
                print("[browser] LI_AT session active.")
                try:
                    yield context, page
                finally:
                    await browser.close()
                return
            else:
                print("[browser] LI_AT cookie is expired — falling through to next auth mode.")

        # ── Mode 2: saved session.json ────────────────────────────────────
        session = _load_session()
        if session:
            print("[browser] Loading saved session cookies...")
            await context.add_cookies(session["cookies"])
            if await _is_logged_in(page):
                print("[browser] Session restored — skipping login.")
                try:
                    yield context, page
                finally:
                    await browser.close()
                return
            print("[browser] Saved session invalid — trying next mode.")

        # ── Mode 3: credential login ──────────────────────────────────────
        use_chrome = os.getenv("CHROME_PROFILE", "").lower() in ("true", "1", "yes")
        if not use_chrome:
            await _login(page)
            _save_session(await context.cookies())
            try:
                yield context, page
            finally:
                await browser.close()
            return

        # ── Mode 4: Chrome profile (Keychain popup) ───────────────────────
        await browser.close()
        async with _chrome_profile_context(pw) as ctx_page:
            yield ctx_page


# ── Standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    async def _test():
        async with get_browser_context() as (ctx, page):
            print(f"[test] URL:   {page.url}")
            print(f"[test] Title: {await page.title()}")
            print("[test] browser.py OK")

    asyncio.run(_test())
