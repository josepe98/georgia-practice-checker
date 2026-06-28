#!/usr/bin/env python3
"""
Checks two pediatrics websites for Georgia practices and emails a report.
Detects when new practices are added.
"""

import json
import os
import re
import smtplib
import sys
import traceback
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "georgia_practices_state.json"
CONFIG_FILE = SCRIPT_DIR / "georgia_checker_config.json"

PLAYGROUND_JOBS_URL = (
    "https://recruiting.paylocity.com/recruiting/jobs/All/"
    "6e778039-ca42-42cf-a3f1-7f072a4a3317/Playground-Management"
)
PLAYGROUND_JOB_DETAIL_URL = (
    "https://recruiting.paylocity.com/recruiting/jobs/Details/{job_id}"
)


def load_config():
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found at {CONFIG_FILE}")
        print("Create it with your email settings. See georgia_checker_config.example.json")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_previous_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"playground": [], "zarminali": [], "playground_jobs_locations": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def scrape_playground_georgia():
    """Scrape Playground Pediatrics for Georgia practices."""
    url = "https://www.playgroundpediatrics.com/our-practices"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    practices = []
    in_georgia = False

    # The site uses headers for states and divs for practices.
    # Walk through all elements looking for Georgia section.
    seen = set()
    for el in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "li", "p", "div"]):
        text = el.get_text(strip=True)
        tag = el.name

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            in_georgia = "georgia" in text.lower()
        elif in_georgia and text:
            # Skip link/button text and state names
            if text in ("Visit Practice Website", "Georgia", "North Carolina",
                        "Pennsylvania", "Tennessee", "Alabama", "Florida",
                        "South Carolina", "Virginia", "Texas"):
                continue
            # Skip city/state lines (e.g. "Marietta, GA")
            if re.search(r',\s*[A-Z]{2}$', text):
                continue
            # Skip long descriptions and concatenated parent divs
            if len(text) > 80:
                continue
            if len(text) <= 3:
                continue
            if text not in seen:
                seen.add(text)
                practices.append(text)

    return practices


def scrape_zarminali_georgia():
    """Scrape Zarminali for Georgia locations, returning clinic names only."""
    url = "https://zarminali.com/locations"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    page_text = soup.get_text()
    lines = [line.strip() for line in page_text.split("\n") if line.strip()]

    # Lines to skip — not location names
    SKIP_LINES = {
        "Make an Appointment", "Book An Appointment",
        "View Location", "Join Priority List", "Coming Soon",
        "Walk-ins welcome", "Offers Telehealth",
        "Primary Care", "Urgent Care", "Primary Care Urgent Care",
    }

    state_keywords = {
        "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
        "Connecticut", "Delaware", "Florida", "Hawaii", "Idaho",
        "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
        "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
        "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
        "New Hampshire", "New Jersey", "New Mexico", "New York",
        "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
        "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
        "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
        "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
        "Washington, D.C."
    }

    in_georgia = False
    location_names = []

    for line in lines:
        if line == "Georgia":
            in_georgia = True
            continue
        if not in_georgia:
            continue
        if line in state_keywords:
            break
        if line in SKIP_LINES:
            continue
        # Skip address lines (contain street/city/state abbreviations and digits)
        if re.search(r'\b(GA|Ave|Rd|St|Dr|Blvd|NE|NW|SE|SW)\b', line) and re.search(r'\d', line):
            continue
        # Skip phone numbers
        if re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', line):
            continue
        location_names.append(line)

    return location_names


def _fetch_job_brand(job_id):
    """Fetch a Paylocity job detail page and return the brand (`moduleName`).

    Returns None on any failure — callers should treat None as 'unknown brand'.
    """
    try:
        resp = requests.get(
            PLAYGROUND_JOB_DETAIL_URL.format(job_id=job_id),
            timeout=30,
        )
        resp.raise_for_status()
        m = re.search(
            r"window\.pageData\s*=\s*(\{.*?\});",
            resp.text,
            re.DOTALL,
        )
        if not m:
            return None
        return json.loads(m.group(1)).get("moduleName") or None
    except Exception as exc:
        print(f"  WARN: could not resolve brand for job {job_id}: {exc}")
        return None


def scrape_playground_jobs_georgia():
    """Scrape Paylocity recruiting page for Playground Management GA jobs.

    The list page embeds all jobs as a `window.pageData = {...}` JSON blob,
    but its `LocationName` field is sometimes the city/state instead of the
    practice brand (e.g. "Warner Robins, GA" actually = Cornerstone Medical
    Associates). The per-job detail page exposes the brand cleanly in
    `window.pageData.moduleName`, so we fetch one detail page per GA job.

    Returns a list of job dicts (sorted by brand, location, title) with keys:
      title, location, brand, is_de_novo, published (YYYY-MM-DD).
    `location` stays as the per-site identifier (preserves distinct de novo
    sites that share a brand); `brand` is the canonical practice name.
    """
    resp = requests.get(PLAYGROUND_JOBS_URL, timeout=30)
    resp.raise_for_status()
    m = re.search(
        r"window\.pageData\s*=\s*(\{.*?\});\s*</script>",
        resp.text,
        re.DOTALL,
    )
    if not m:
        return []
    data = json.loads(m.group(1))

    jobs = []
    for j in data.get("Jobs", []):
        loc = j.get("JobLocation") or {}
        if loc.get("State") != "GA":
            continue
        location = j.get("LocationName") or loc.get("Name") or ""
        brand = _fetch_job_brand(j.get("JobId"))
        jobs.append({
            "title": j.get("JobTitle", ""),
            "location": location,
            "brand": brand,
            "is_de_novo": "(De Novo)" in location,
            "published": (j.get("PublishedDate") or "")[:10],
        })

    jobs.sort(key=lambda j: (j["brand"] or "", j["location"], j["title"]))
    return jobs


def build_email(playground, zarminali, jobs,
                new_playground, new_zarminali, new_site_locations):
    """Build the email body."""
    lines = []
    lines.append("Georgia Pediatric Practice Report")
    lines.append("=" * 40)
    lines.append("")

    # New practice alerts
    if new_playground or new_zarminali or new_site_locations:
        lines.append("🔔 NEW PRACTICES DETECTED!")
        lines.append("-" * 30)
        if new_playground:
            lines.append("New on Playground Pediatrics:")
            for p in new_playground:
                lines.append(f"  ★ {p}")
        if new_zarminali:
            lines.append("New on Zarminali:")
            for z in new_zarminali:
                lines.append(f"  ★ {z}")
        if new_site_locations:
            lines.append("New GA sites on Playground (via Paylocity recruiting):")
            for loc in new_site_locations:
                tag = "  ★ [DE NOVO] " if "(De Novo)" in loc else "  ★ "
                lines.append(f"{tag}{loc}")
        lines.append("")

    lines.append("Current Georgia Practices — Playground Pediatrics")
    lines.append("-" * 30)
    if playground:
        for p in playground:
            lines.append(f"  • {p}")
    else:
        lines.append("  (none found)")
    lines.append("")

    lines.append("Current Georgia Locations — Zarminali")
    lines.append("-" * 30)
    if zarminali:
        for z in zarminali:
            lines.append(f"  • {z}")
    else:
        lines.append("  (none found)")

    lines.append("")
    lines.append("Georgia Job Postings — Playground (Paylocity)")
    lines.append("-" * 30)
    if jobs:
        for j in jobs:
            tag = " [DE NOVO]" if j["is_de_novo"] else ""
            brand = j["brand"] or "?"
            # When the listing's LocationName already matches the brand (e.g. a
            # job at "Jonesboro Pediatrics"), don't repeat it.
            if j["location"] and j["location"] != brand:
                header = f"{brand} — {j['location']}{tag}"
            else:
                header = f"{brand}{tag}"
            lines.append(f"  • {header}")
            lines.append(f"      {j['title']} (posted {j['published']})")
    else:
        lines.append("  (none found)")

    lines.append("")
    lines.append("Sources:")
    lines.append("  https://www.playgroundpediatrics.com/our-practices")
    lines.append("  https://zarminali.com/locations")
    lines.append(f"  {PLAYGROUND_JOBS_URL}")

    return "\n".join(lines)


def send_email(config, subject, body):
    """Send email via Fastmail SMTP."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config["from_email"]
    msg["To"] = config["to_email"]

    with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
        server.starttls()
        server.login(config["smtp_user"], config["smtp_password"])
        server.send_message(msg)


def send_error_email(config, error):
    """Send an error alert when the main report email can't fire."""
    admin = config.get("admin_email", config.get("to_email", ""))
    if not admin:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subject = f"[Georgia Checker] ERROR – {now}"
    body = f"Georgia practice checker failed at {now}:\n\n{error}"
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config["from_email"]
        msg["To"] = admin
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)
        print("Error email sent.")
    except Exception as exc:
        print(f"Could not send error email: {exc}")


def main():
    config = load_config()
    try:
        print("Scraping Playground Pediatrics...")
        playground = scrape_playground_georgia()
        print(f"  Found {len(playground)} Georgia practice(s)")

        print("Scraping Zarminali...")
        zarminali = scrape_zarminali_georgia()
        print(f"  Found {len(zarminali)} Georgia location(s)")

        print("Scraping Playground recruiting (Paylocity)...")
        jobs = scrape_playground_jobs_georgia()
        job_locations = sorted({j["location"] for j in jobs if j["location"]})
        print(f"  Found {len(jobs)} GA job(s) across {len(job_locations)} location(s)")

        previous = load_previous_state()
        new_playground = [p for p in playground if p not in previous.get("playground", [])]
        new_zarminali = [z for z in zarminali if z not in previous.get("zarminali", [])]
        # Treat the jobs section as "first run" if its state key is missing — avoids
        # flagging every current GA hiring location as new the first time this runs.
        jobs_previously_tracked = "playground_jobs_locations" in previous
        # A job points at a new site if its location is one we haven't seen AND
        # either it's flagged "(De Novo)" or its resolved brand isn't already on
        # the practices page (e.g. Jonesboro Pediatrics) — postings at existing
        # acquired practices (e.g. Cornerstone-branded Warner Robins jobs) are
        # not "new sites" even when the LocationName looks unfamiliar.
        known_brands = set(playground)
        seen_locations = set(previous.get("playground_jobs_locations", []))
        new_site_locations = sorted({
            j["location"] for j in jobs
            if j["location"]
            and j["location"] not in seen_locations
            and (j["is_de_novo"] or (j["brand"] and j["brand"] not in known_brands))
        }) if jobs_previously_tracked else []

        is_first_run = not STATE_FILE.exists()

        subject = "Georgia Pediatric Practice Report"
        if not is_first_run and (new_playground or new_zarminali or new_site_locations):
            subject = "🔔 New Georgia Practice Detected!"

        body = build_email(
            playground, zarminali, jobs,
            new_playground if not is_first_run else [],
            new_zarminali if not is_first_run else [],
            new_site_locations if not is_first_run else [],
        )

        print("Sending email...")
        send_email(config, subject, body)
        print("Email sent.")

        save_state({
            "playground": playground,
            "zarminali": zarminali,
            "playground_jobs_locations": job_locations,
        })
        print("State saved.")
    except Exception as exc:
        print(f"ERROR: {exc}")
        send_error_email(config, f"{exc}\n\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
