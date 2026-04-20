# georgia-practice-checker

A Python scraper that monitors two pediatric practice websites — Playground Pediatrics and Zarminali Pediatrics — for new Georgia locations and emails a weekly report.

## What it does

- Scrapes each practice's locations page and filters to Georgia
- Compares against a saved state file to detect new practices
- Sends a formatted email report every Monday
- Highlights new additions with an alert in the subject line
- Emails a stack trace on failure

## Stack

Python 3, `requests`, `beautifulsoup4`, SMTP

## Setup

1. Copy the example config and fill in your SMTP credentials:
   ```bash
   cp georgia_checker_config.example.json georgia_checker_config.json
   ```
2. Install dependencies:
   ```bash
   pip install requests beautifulsoup4
   ```
3. Run manually:
   ```bash
   python3 georgia_practice_checker.py
   ```

## Schedule (macOS)

Copy the included LaunchAgent plist to `~/Library/LaunchAgents/` to run every Monday at 9 AM.

## License

MIT
