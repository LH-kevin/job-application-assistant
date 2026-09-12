#!/usr/bin/env python3
"""
search_target_companies.py

Search job aggregators for companies currently hiring for a given role, and
return a deduplicated list of {company, title, location, posting_url, source}.

REQUIRES NETWORK ACCESS. This sandbox has network disabled for bash_tool, so
this script is written for the *user's own* Claude Code / Codex environment
(or any environment with outbound internet). If run here it will fail fast
with a clear message rather than hanging.

Usage:
    python search_target_companies.py "前端工程师" --location "上海" --limit 30
    python search_target_companies.py "Product Manager" --location "Remote" \
        --sources linkedin,indeed

Design notes:
- This does NOT scrape logged-in-only pages or bypass any paywall/CAPTCHA.
  Every source below has a public search results page usable without login;
  if a site changes its markup or starts requiring login, that source will
  simply return zero results and should be swapped for an official API where
  one exists (e.g. GitHub Jobs-style feeds, greenhouse.io's public job board
  JSON endpoints, a licensed job-board API key, etc).
- Prefer official APIs over HTML scraping wherever the target site offers one
  (Greenhouse's `boards-api.greenhouse.io/v1/boards/<token>/jobs` is a good
  example of a clean, ToS-friendly public endpoint).
"""
import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from urllib.parse import quote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print(
        "Missing deps. Install with:\n"
        "    pip install requests beautifulsoup4 --break-system-packages\n",
        file=sys.stderr,
    )
    sys.exit(1)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; job-application-assistant/1.0; "
        "+for personal job-search use)"
    )
}
TIMEOUT = 10


@dataclass
class Posting:
    company: str
    title: str
    location: str
    posting_url: str
    source: str


def _get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp


def search_indeed(role: str, location: str, limit: int) -> list[Posting]:
    """Public Indeed search results page (no login required)."""
    out: list[Posting] = []
    try:
        url = "https://www.indeed.com/jobs"
        resp = _get(url, params={"q": role, "l": location})
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job_seen_beacon") or soup.select(
            "a.tapItem"
        )
        for card in cards[:limit]:
            company_el = card.select_one(".companyName")
            title_el = card.select_one("h2.jobTitle span") or card.select_one(
                ".jobTitle"
            )
            loc_el = card.select_one(".companyLocation")
            link_el = card.select_one("a")
            if not (company_el and title_el and link_el):
                continue
            href = link_el.get("href", "")
            full_url = (
                href if href.startswith("http") else f"https://www.indeed.com{href}"
            )
            out.append(
                Posting(
                    company=company_el.get_text(strip=True),
                    title=title_el.get_text(strip=True),
                    location=loc_el.get_text(strip=True) if loc_el else location,
                    posting_url=full_url,
                    source="indeed",
                )
            )
    except Exception as e:  # noqa: BLE001
        print(f"[indeed] search failed: {e}", file=sys.stderr)
    return out


def search_linkedin(role: str, location: str, limit: int) -> list[Posting]:
    """
    LinkedIn's public job-search guest endpoint. LinkedIn aggressively rate
    limits / blocks scraping — treat this as best-effort, low-volume, and
    switch to LinkedIn's official Talent/Jobs API if you need reliability.
    """
    out: list[Posting] = []
    try:
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        resp = _get(
            url,
            params={
                "keywords": role,
                "location": location,
                "start": 0,
            },
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("li")
        for card in cards[:limit]:
            title_el = card.select_one(".base-search-card__title")
            company_el = card.select_one(".base-search-card__subtitle")
            loc_el = card.select_one(".job-search-card__location")
            link_el = card.select_one("a.base-card__full-link")
            if not (title_el and company_el and link_el):
                continue
            out.append(
                Posting(
                    company=company_el.get_text(strip=True),
                    title=title_el.get_text(strip=True),
                    location=loc_el.get_text(strip=True) if loc_el else location,
                    posting_url=link_el.get("href", "").split("?")[0],
                    source="linkedin",
                )
            )
    except Exception as e:  # noqa: BLE001
        print(f"[linkedin] search failed: {e}", file=sys.stderr)
    return out


def search_zhaopin_cn(role: str, location: str, limit: int) -> list[Posting]:
    """
    Placeholder for a China-focused source (智联招聘 / 猎聘 / BOSS直聘).
    These sites require signed API params or app-only endpoints and change
    frequently, so wire this up against whichever one you have legitimate
    API access to, or use their official open-platform APIs if available.
    """
    print(
        "[zhaopin_cn] not implemented — plug in an official API "
        "(e.g. 智联招聘开放平台) or a licensed job-board data provider here.",
        file=sys.stderr,
    )
    return []


SOURCES = {
    "indeed": search_indeed,
    "linkedin": search_linkedin,
    "zhaopin_cn": search_zhaopin_cn,
}


def dedupe(postings: list[Posting]) -> list[Posting]:
    seen = set()
    result = []
    for p in postings:
        key = (p.company.strip().lower(), p.title.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(p)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", help="Job title/role to search for")
    parser.add_argument("--location", default="", help="City / 'Remote' / etc.")
    parser.add_argument("--limit", type=int, default=25, help="Max results per source")
    parser.add_argument(
        "--sources",
        default="indeed,linkedin",
        help="Comma-separated source list: " + ",".join(SOURCES.keys()),
    )
    parser.add_argument("--out", default="", help="Write JSON results to this file")
    args = parser.parse_args()

    all_postings: list[Posting] = []
    for name in args.sources.split(","):
        name = name.strip()
        fn = SOURCES.get(name)
        if not fn:
            print(f"Unknown source: {name}", file=sys.stderr)
            continue
        all_postings.extend(fn(args.role, args.location, args.limit))
        time.sleep(1)  # be polite between sources

    all_postings = dedupe(all_postings)

    payload = [asdict(p) for p in all_postings]
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {len(payload)} postings to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
