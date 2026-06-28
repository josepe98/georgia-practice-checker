# Georgia Practice Checker — Requirements

## Purpose
Monitor two pediatric practice websites for new Georgia locations and send a weekly email report. Alert immediately (via subject line) when a new practice is detected.

## Functional Requirements

1. **Scrape Playground Pediatrics** (`https://www.playgroundpediatrics.com/our-practices`) for Georgia practice names.
2. **Scrape Zarminali** (`https://zarminali.com/locations`) for Georgia location names.
3. **Monitor Paylocity recruiting** for Playground Management job postings to detect new Georgia sites. Resolve practice brand via job detail page to handle cases where `LocationName` is ambiguous (e.g., city/state instead of brand). Tag de novo sites.
4. **Detect new practices and sites** by comparing current scrape results against previously saved state. For job-based detection, only flag as new if the site location is previously unseen AND either flagged as de novo OR the resolved brand is not already on the main practices page.
5. **Send an email report** after every run containing:
   - A new-practice alert section (if any new practices, locations, or sites were found and it is not the first run)
   - The full current list of Georgia practices from both sites
   - A list of current Georgia job postings from Playlocity recruiting, grouped by brand and location
   - Source URLs
6. **Email subject** should be `"Georgia Pediatric Practice Report"` normally, or `"🔔 New Georgia Practice Detected!"` when new entries are found.
7. **Persist state** to `georgia_practices_state.json` after each run (including tracked job locations) so future runs can detect changes.
8. **Run weekly** — every Monday at 9 AM via macOS LaunchAgent.
9. **Send an error alert email** to the admin if any unhandled exception prevents the main report email from firing. The error email must include the exception message and full stack trace.

## Non-Functional Requirements

- Email sent via Fastmail SMTP (configured in `georgia_checker_config.json`)
- Config file must not be committed with real credentials — use `georgia_checker_config.example.json` as a template
- Script must be runnable manually for testing
- Errors and output logged to `georgia_checker.log`

## Configuration

| Key | Description |
|-----|-------------|
| `smtp_host` | SMTP server hostname |
| `smtp_port` | SMTP port (587 for STARTTLS) |
| `smtp_user` | SMTP login username |
| `smtp_password` | App-specific password |
| `from_email` | Sender address |
| `to_email` | Recipient address |
| `admin_email` | Error alert recipient (optional — falls back to `to_email`) |

## Dependencies

- Python 3
- `requests` (HTTP fetching)
- `beautifulsoup4` (HTML parsing)
- `re` (regex for JSON extraction from embedded `window.pageData` blobs)
