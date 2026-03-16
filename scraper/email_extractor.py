"""
email_extractor.py — Regex-based email extraction from post text.
Handles standard emails and common obfuscation patterns.
"""

import re

# Standard email
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Obfuscated: "john at gmail dot com", "john[at]gmail[dot]com"
_OBFUSCATED_RE = re.compile(
    r"([\w.+\-]+)"           # local part
    r"\s*(?:\[|\()?(?:at|@)(?:\]|\))?\s*"  # at / @ (optionally bracketed)
    r"([\w\-]+)"             # domain name
    r"\s*(?:\[|\()?(?:dot|\.)(?:\]|\))?\s*"  # dot (optionally bracketed)
    r"([a-zA-Z]{2,})",       # TLD
    re.IGNORECASE,
)

# Block-listed domains that produce false positives
_BLOCKLIST = {"example.com", "test.com", "domain.com", "email.com"}

# Only accept real TLDs: 2-6 chars, letters only, known suffix
# This prevents matching sentence fragments like "scratch.Vision" → "scr@ch.vision"
_VALID_TLD_RE = re.compile(
    r"^(com|org|net|edu|gov|mil|int|io|co|ai|app|dev|tech|me|us|uk|ca|au|in|"
    r"de|fr|jp|cn|br|mx|ru|nl|se|no|dk|fi|sg|nz|za|ae|info|biz|mobi|name|"
    r"pro|aero|coop|museum|travel|jobs|tel|cat|post|xxx|asia|tel|"
    r"cloud|digital|online|site|store|shop|blog|media|agency|studio|"
    r"email|mail|work|careers|team|group|inc|ltd|llc|corp)$",
    re.IGNORECASE,
)


def _clean(email: str) -> str:
    return email.strip().lower()


def _valid(email: str) -> bool:
    """Return True only if the email has a realistic TLD and local part."""
    parts = email.rsplit("@", 1)
    if len(parts) != 2:
        return False
    local, domain = parts
    # Local part must be at least 2 chars
    if len(local) < 2:
        return False
    # Domain blocklist
    if domain in _BLOCKLIST:
        return False
    # TLD must be known/real
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    if not _VALID_TLD_RE.match(tld):
        return False
    return True


def extract_emails(text: str) -> list[str]:
    """
    Extract and return a deduplicated list of email addresses from `text`.
    Returns emails in lowercase, sorted.
    """
    found: set[str] = set()

    for m in _EMAIL_RE.findall(text):
        e = _clean(m)
        if _valid(e):
            found.add(e)

    for m in _OBFUSCATED_RE.findall(text):
        e = _clean(f"{m[0]}@{m[1]}.{m[2]}")
        if _valid(e):
            found.add(e)

    return sorted(found)
