#!/usr/bin/env python3
"""
ats_form_filler.py

Playwright-based template for filling common ATS (Applicant Tracking System)
application forms. This is a REFERENCE IMPLEMENTATION, not a fire-and-forget
script — ATS forms vary, and this deliberately STOPS before the final submit
click so a human can review.

Requires:
    pip install playwright --break-system-packages
    playwright install chromium

Usage:
    python ats_form_filler.py \
        --url "https://boards.greenhouse.io/acme/jobs/12345" \
        --ats greenhouse \
        --name "Zhang Wei" --email "wei@example.com" --phone "+86 138..." \
        --resume "/path/to/resume.pdf" \
        --cover-letter "/path/to/cover_letter.pdf"

Behavior:
    1. Opens the page in a VISIBLE (headless=False) browser window by
       default — this is required so a human can see and manually solve
       any CAPTCHA/human-verification challenge the site throws up. Running
       headless hides the challenge entirely, which just looks like the
       script "getting stuck" with no way to respond. Pass --headless only
       if you specifically need a headless run and are confident the target
       form has no bot-check (rare).
    2. Detects/confirms the ATS type (or uses --ats if given).
    3. Checks for a CAPTCHA/anti-bot challenge on the page before filling
       anything (reCAPTCHA/hCaptcha iframe, Cloudflare challenge markers).
       If one is found, the script STOPS and waits at the terminal for you
       to solve it by hand in the visible window, then press Enter to
       continue. It never attempts to solve or bypass the challenge itself.
    4. Fills the known field set for that ATS from references/ats_platforms.md.
    5. Uploads resume/cover letter if fields exist.
    6. Takes a screenshot of the filled form and saves it locally.
    7. PAUSES — prints the screenshot path and a summary, and exits WITHOUT
       clicking submit. A human (or the calling agent, after explicit user
       go-ahead) must run the separate `--confirm-submit` pass to finish.
"""
import argparse
import sys
import time

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print(
        "Missing dep. Install with:\n"
        "    pip install playwright --break-system-packages\n"
        "    playwright install chromium\n",
        file=sys.stderr,
    )
    sys.exit(1)


# Field selector maps per ATS. These are best-effort and DOM structures
# change over time — verify against the live page and update as needed.
ATS_FIELD_MAP = {
    "greenhouse": {
        "name_first": "input#first_name",
        "name_last": "input#last_name",
        "email": "input#email",
        "phone": "input#phone",
        "resume_upload": "input[type=file][name='resume']",
        "cover_letter_upload": "input[type=file][name='cover_letter']",
        "submit_button": "input[type=submit], button#submit_app",
    },
    "lever": {
        "name": "input[name='name']",
        "email": "input[name='email']",
        "phone": "input[name='phone']",
        "resume_upload": "input[name='resume']",
        "submit_button": "button[type='submit']",
    },
    "workday": {
        # Workday is a heavily JS-driven multi-step wizard; selectors are
        # highly tenant-specific. Treat this as a starting point only —
        # you will likely need to record actual selectors per company via
        # the browser tool's inspector before this works reliably.
        "name_first": "input[data-automation-id='legalNameSection_firstName']",
        "name_last": "input[data-automation-id='legalNameSection_lastName']",
        "email": "input[data-automation-id='email']",
        "resume_upload": "input[data-automation-id='file-upload-input-ref']",
        "submit_button": "button[data-automation-id='bottom-navigation-next-button']",
    },
}


CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[title*='recaptcha' i]",
    "iframe[src*='hcaptcha']",
    "div#challenge-form",             # Cloudflare challenge page
    "div.cf-turnstile",               # Cloudflare Turnstile
    "iframe[src*='turnstile']",
]


def detect_captcha(page) -> bool:
    for selector in CAPTCHA_SELECTORS:
        try:
            if page.locator(selector).count() > 0:
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def wait_for_manual_captcha_solve(page) -> None:
    """Never attempts to solve or bypass the challenge. Just makes sure a
    human can see it (headless=False is required for this to work) and
    pauses the script until they've dealt with it."""
    print(
        "\n🔒 A CAPTCHA / human-verification challenge was detected on this "
        "page.\nThe browser window is open — please solve it manually there, "
        "then come back to this terminal.\n"
    )
    input("Press Enter here once you've solved it and the page has moved on... ")


def detect_ats(url: str) -> str | None:
    if "greenhouse.io" in url:
        return "greenhouse"
    if "lever.co" in url:
        return "lever"
    if "myworkdayjobs.com" in url:
        return "workday"
    return None


def fill_form(page, ats: str, args) -> None:
    fields = ATS_FIELD_MAP.get(ats)
    if not fields:
        raise ValueError(
            f"No field map for ATS '{ats}'. Add one to ATS_FIELD_MAP after "
            "inspecting the live form, or fill manually."
        )

    def try_fill(selector_key, value):
        selector = fields.get(selector_key)
        if not selector or not value:
            return
        try:
            page.fill(selector, value, timeout=3000)
        except Exception as e:  # noqa: BLE001
            print(f"  (skip) could not fill {selector_key}: {e}", file=sys.stderr)

    if "name_first" in fields and args.name:
        first, *rest = args.name.split(" ", 1)
        try_fill("name_first", first)
        if rest:
            try_fill("name_last", rest[0])
    elif "name" in fields:
        try_fill("name", args.name)

    try_fill("email", args.email)
    try_fill("phone", args.phone)

    if args.resume and fields.get("resume_upload"):
        try:
            page.set_input_files(fields["resume_upload"], args.resume)
        except Exception as e:  # noqa: BLE001
            print(f"  (skip) resume upload failed: {e}", file=sys.stderr)

    if args.cover_letter and fields.get("cover_letter_upload"):
        try:
            page.set_input_files(fields["cover_letter_upload"], args.cover_letter)
        except Exception as e:  # noqa: BLE001
            print(f"  (skip) cover letter upload failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--ats", default="", help="greenhouse|lever|workday (auto-detected if omitted)")
    parser.add_argument("--name", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--phone", default="")
    parser.add_argument("--resume", default="")
    parser.add_argument("--cover-letter", default="")
    parser.add_argument("--screenshot-out", default="filled_form.png")
    parser.add_argument(
        "--confirm-submit",
        action="store_true",
        help="Only pass this after the user has explicitly reviewed and "
        "approved the filled form. Without it, the script never clicks submit.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible window. NOT recommended: if the site "
        "shows a CAPTCHA, a headless run cannot be solved by a human. Only "
        "use this when you're confident the target form has no bot-check.",
    )
    args = parser.parse_args()

    ats = args.ats or detect_ats(args.url)
    if not ats:
        print(
            "Could not auto-detect ATS from URL. Pass --ats explicitly, or "
            "check references/ats_platforms.md for fingerprints.",
            file=sys.stderr,
        )
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto(args.url, timeout=20000)
        time.sleep(1)

        if detect_captcha(page):
            if args.headless:
                print(
                    "CAPTCHA detected but running headless — a human can't "
                    "see it to solve it. Re-run without --headless.",
                    file=sys.stderr,
                )
                browser.close()
                sys.exit(1)
            wait_for_manual_captcha_solve(page)

        fill_form(page, ats, args)

        # Check again after filling — some forms only trigger the challenge
        # once fields are touched or on attempted submit.
        if detect_captcha(page):
            if args.headless:
                print(
                    "CAPTCHA appeared after filling, but running headless.",
                    file=sys.stderr,
                )
                browser.close()
                sys.exit(1)
            wait_for_manual_captcha_solve(page)

        page.screenshot(path=args.screenshot_out, full_page=True)
        print(f"Filled form screenshot saved to: {args.screenshot_out}")

        if args.confirm_submit:
            fields = ATS_FIELD_MAP[ats]
            submit_selector = fields.get("submit_button")
            if not submit_selector:
                print("No submit selector mapped for this ATS.", file=sys.stderr)
            else:
                page.click(submit_selector, timeout=5000)
                time.sleep(2)
                if detect_captcha(page):
                    print(
                        "CAPTCHA appeared right at submit — solve it manually "
                        "in the window, then check the page yourself to "
                        "confirm whether the application actually went "
                        "through (don't assume success).",
                    )
                    if not args.headless:
                        wait_for_manual_captcha_solve(page)
                else:
                    print("Submitted.")
        else:
            print(
                "NOT submitted — review the screenshot, then re-run with "
                "--confirm-submit once the user explicitly approves."
            )

        browser.close()


if __name__ == "__main__":
    main()
