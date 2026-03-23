# CLAUDE.md — DS Job Agent

This file tells Claude Code exactly how to help with this project.

## Project purpose
Automated job alert agent for Deekshita Sridhar — searches Indeed UK every 8 hours,
tailors resume and cover letter per job using Claude API, produces an HTML report.

## How to run
```bash
pip install anthropic requests python-dotenv schedule
python agent.py
```

## Key files
- `agent.py` — main agent (search → tailor → report → email)
- `.env` — API keys (copy from .env.template and fill in)
- `reports/` — generated HTML reports (one per run)
- `seen_jobs.json` — tracks already-seen jobs to avoid duplicates

## When Claude Code should help with this project
- If the Indeed API (RapidAPI) stops working → update the `search_indeed()` function
- If I want to add more job search terms → update the `SEARCHES` list in agent.py
- If I want to change salary filter → update `MIN_SALARY` in agent.py
- If I want to add LinkedIn search → add a new search function alongside `search_indeed()`
- If the HTML report needs redesigning → update `generate_html_report()`
- If I want to add WhatsApp alerts instead of email → replace `send_email()` with Twilio

## Candidate profile
All candidate details are in the `CANDIDATE` dict in agent.py.
Update this dict if resume changes — the tailoring prompts use it.

## Common tasks for Claude Code
1. "The search isn't returning results" → debug search_indeed(), check API key
2. "Add more job search terms" → update SEARCHES list
3. "Make the HTML report look better" → update generate_html_report()
4. "Send alerts to WhatsApp instead" → replace send_email() with Twilio API
5. "Add a LinkedIn scraper" → add new function, import into run()
6. "Schedule this on Windows Task Scheduler" → create a .bat file wrapper
