# georgia-practice-checker

A Python scraper that monitors Playground Pediatrics, Zarminali Pediatrics, and Playground recruiting activity for new Georgia practice locations and emails a weekly report.

## What it does

- Scrapes Playground Pediatrics and Zarminali locations pages for Georgia practices
- Monitors Paylocity recruiting for Playground Management job postings in Georgia
- Resolves practice brand from job detail pages to handle ambiguous location names
- Compares against saved state to detect new practices and sites
- Sends a formatted email report every Monday with current practices and open job postings
- Highlights new additions with an alert in the subject line (`🔔 New Georgia Practice Detected!`)
- Tags de novo practice sites when detected through recruiting
- Sends error alerts with stack traces if the script fails

## Stack

Python 3, `requests`, `beautifulsoup4`, SMTP, regex (for JSON extraction from embedded page data)

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
