# Georgia Practice Checker — Requirements

## Purpose
Monitor two pediatric practice websites for new Georgia locations and send a weekly email report. Alert immediately (via subject line) when a new practice is detected.

## Functional Requirements

1. **Scrape Playground Pediatrics** (`https://www.playgroundpediatrics.com/our-practices`) for Georgia practice names.
2. **Scrape Zarminali** (`https://zarminali.com/locations`) for Georgia location names.
3. **Detect new practices** by comparing current scrape results against previously saved state.
4. **Send an email report** after every run containing:
   - A new-practice alert section (if any new entries were found and it is not the first run)
   - The full current list of Georgia practices from both sites
   - Source URLs
5. **Email subject** should be `"Georgia Pediatric Practice Report"` normally, or `"🔔 New Georgia Practice Detected!"` when new entries are found.
6. **Persist state** to `georgia_practices_state.json` after each run so future runs can detect changes.
7. **Run weekly** — every Monday at 9 AM via macOS LaunchAgent.

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

## Dependencies

- Python 3
- `requests`
- `beautifulsoup4`
