"""
generator.py — Generate personalized outreach email drafts.

Two modes:
  1. Template-based (default): Jinja2 substitution, no API key required.
  2. AI-based (optional): Calls Claude API for more personalized drafts.
     Requires ANTHROPIC_API_KEY in .env and use_ai_outreach=true in config.json.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
CONFIG_FILE = Path(__file__).parent.parent / "config.json"

_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

ROLE_TARGET = "Staff / Principal SDET or Test Automation Engineer"  # Swapnil's target level


def _snippet(post_text: str, max_chars: int = 120) -> str:
    """Return a short, readable excerpt from the post text."""
    if not post_text:
        return "Your recent post caught my attention."
    clean = " ".join(post_text.split())
    if len(clean) <= max_chars:
        return f'I noticed your post: "{clean}"'
    return f'I noticed your post: "{clean[:max_chars].rsplit(" ", 1)[0]}…"'


def _generate_template(lead: dict) -> dict:
    """Generate a draft using the Jinja2 template."""
    template = _jinja_env.get_template("email_template.txt")
    rendered = template.render(
        author_name=lead.get("author_name", ""),
        post_snippet=_snippet(lead.get("post_text", "")),
        role_target=ROLE_TARGET,
    )
    lines = rendered.strip().splitlines()
    subject = lines[0].replace("Subject: ", "").strip() if lines else "Quick note"
    body = "\n".join(lines[2:]).strip()  # skip subject + blank line
    return {"subject": subject, "body": body}


def _generate_ai(lead: dict) -> dict:
    """Generate a draft using the Claude API."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = (
            f"Write a short, friendly cold outreach email to {lead.get('author_name', 'this person')} "
            f"who posted on LinkedIn. Their title is: {lead.get('author_title', 'unknown')}. "
            f"Post context: {_snippet(lead.get('post_text', ''))}. "
            f"I'm looking for {ROLE_TARGET} roles. "
            f"Keep it under 100 words. Return only the email body (no subject line)."
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        body = message.content[0].text.strip()
        first_name = lead.get("author_name", "").split()[0] if lead.get("author_name") else "Hi"
        return {"subject": f"Quick note — {first_name}", "body": body}
    except Exception as e:
        print(f"[outreach] AI generation failed ({e}), falling back to template.")
        return _generate_template(lead)


def generate_drafts(leads: list[dict]) -> list[dict]:
    """
    Generate outreach drafts for a list of lead dicts.
    Each lead dict should have: email, author_name, author_title, post_url, post_text (optional).

    Returns list of outreach draft dicts ready for storage.append_outreach().
    """
    config = json.loads(CONFIG_FILE.read_text())
    use_ai = config.get("use_ai_outreach", False)

    results = []
    for lead in leads:
        if not lead.get("email"):
            continue  # skip leads without email (can't send drafts)

        draft = _generate_ai(lead) if use_ai else _generate_template(lead)
        results.append({
            "email": lead["email"],
            "author_name": lead.get("author_name", ""),
            "subject": draft["subject"],
            "body": draft["body"],
            "post_url": lead.get("post_url", ""),
            "generated_at": datetime.utcnow().isoformat(),
        })

    return results
