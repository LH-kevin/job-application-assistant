#!/usr/bin/env python3
"""
find_career_page.py

Given a company name, try to find its OFFICIAL careers/jobs page (as opposed
to a third-party aggregator mirror of the same listing). REQUIRES NETWORK.

Usage:
    python find_career_page.py "Acme Corp"
    python find_career_page.py "Acme Corp" --homepage https://acme.com

Strategy:
1. If a homepage URL isn't given, search for "<company> official site" and
   take the top plausible result (heuristic: domain looks like the company
   name, not a news/wiki/social aggregator).
2. Probe common careers paths on that domain (/careers, /jobs, /about/careers,
   /careers/jobs, /en/careers, etc).
3. Also check for well-known ATS subdomains (boards.greenhouse.io/<company>,
   jobs.lever.co/<company>, <company>.wd1.myworkdayjobs.com, etc) since many
   companies host applications there while *linking* from their own domain —
   that's still their official channel, just hosted by a vendor.
4. Return the first working candidate with a confidence note; return all
   candidates checked so the user/agent can pick if the top one is wrong.
"""
import argparse
import sys
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print(
        "Missing deps. Install with: pip install requests --break-system-packages",
        file=sys.stderr,
    )
    sys.exit(1)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-application-assistant/1.0)"}
TIMEOUT = 8

COMMON_CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/about/careers",
    "/company/careers",
    "/en/careers",
    "/careers/jobs",
    "/join-us",
    "/work-with-us",
    "/zh/careers",
    "/about-us/careers",
]

ATS_SUBDOMAIN_PATTERNS = [
    "https://boards.greenhouse.io/{slug}",
    "https://jobs.lever.co/{slug}",
    "https://{slug}.wd1.myworkdayjobs.com",
    "https://{slug}.wd5.myworkdayjobs.com",
    "https://apply.workable.com/{slug}",
    "https://{slug}.bamboohr.com/jobs",
    "https://{slug}.recruitee.com",
]


def slugify(name: str) -> str:
    return "".join(c.lower() for c in name if c.isalnum())


def probe(url: str) -> bool:
    try:
        resp = requests.head(
            url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True
        )
        if resp.status_code == 405:  # some servers reject HEAD
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        return resp.status_code < 400
    except requests.RequestException:
        return False


def guess_homepage(company: str) -> str | None:
    """
    Best-effort: try the obvious <slug>.com first. For a robust answer,
    prefer resolving this via a real web_search tool in the calling agent
    (e.g. Claude's web_search) and passing --homepage explicitly — this
    local guess is only a fallback.
    """
    slug = slugify(company)
    for tld in (".com", ".io", ".ai", ".co"):
        candidate = f"https://www.{slug}{tld}"
        if probe(candidate):
            return candidate
    return None


def find_career_candidates(homepage: str, company: str) -> list[dict]:
    candidates = []
    domain = urlparse(homepage).netloc
    for path in COMMON_CAREER_PATHS:
        url = f"https://{domain}{path}"
        if probe(url):
            candidates.append(
                {"url": url, "confidence": "high", "reason": "on company domain"}
            )

    slug = slugify(company)
    for pattern in ATS_SUBDOMAIN_PATTERNS:
        url = pattern.format(slug=slug)
        if probe(url):
            candidates.append(
                {
                    "url": url,
                    "confidence": "medium",
                    "reason": "known ATS vendor, guessed slug — verify it's this company",
                }
            )
    return candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("company", help="Company name")
    parser.add_argument(
        "--homepage",
        default="",
        help="Known homepage URL (skip guessing). Recommended: resolve this "
        "via a real search tool first for accuracy.",
    )
    args = parser.parse_args()

    homepage = args.homepage or guess_homepage(args.company)
    if not homepage:
        print(
            f"Could not guess a homepage for '{args.company}'. "
            "Pass --homepage explicitly after finding it via web search.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Homepage: {homepage}")
    candidates = find_career_candidates(homepage, args.company)
    if not candidates:
        print("No careers page found via common paths or known ATS vendors.")
        print(
            "Fall back to: (1) the aggregator listing found earlier, or "
            "(2) a manual web_search for '<company> careers official site'."
        )
        return

    print("Candidate career pages (best first):")
    for c in candidates:
        print(f"  [{c['confidence']}] {c['url']}  ({c['reason']})")


if __name__ == "__main__":
    main()
