# DS Job Alert Agent 🤖

An automated job search agent that runs every 8 hours, finds Data Scientist roles in the UK, and uses Claude AI to tailor your resume summary and cover letter for each job — so you only need to click Apply.

## What it does

- 🔍 **Searches Indeed UK** every 8 hours for Data Scientist, ML Engineer, and Analytics Engineer roles
- 🧠 **Reads each job description** automatically
- ✍️ **Tailors your resume summary** to match each JD using Claude AI
- 📝 **Writes a personalised cover letter** per job
- 📊 **Generates an HTML report** that opens in your browser — one click to apply
- 📧 **Emails you the report** so you never miss a new role
- ✅ **Tracks seen jobs** so you never see duplicates

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/ds-job-agent.git
cd ds-job-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up API keys
```bash
cp .env.template .env
```
Edit `.env` with your keys:

| Key | Where to get it |
|-----|----------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `RAPIDAPI_KEY` | [rapidapi.com](https://rapidapi.com) → search "indeed12" → free tier |
| `EMAIL_FROM` | Your Gmail address |
| `EMAIL_PASSWORD` | Gmail → Settings → Security → App Passwords |

### 4. Update your profile
Open `agent.py` and edit the `CANDIDATE` dict with your details.

### 5. Run
```bash
python agent.py
```

## Scheduling

**Windows:** Task Scheduler → run `agent.py` → repeat every 8 hours

**Mac/Linux:**
```bash
crontab -e
# Add: 0 */8 * * * python3 /path/to/agent.py
```

## Customise searches

```python
SEARCHES = [
    {"search": "Data Scientist", "location": "London"},
    {"search": "ML Engineer",    "location": "remote"},
]
MIN_SALARY = 55000
```

## Using with Claude Code in Cursor

Open this folder in Cursor. Claude Code reads `CLAUDE.md` automatically and understands the whole project. Ask it to add features, fix bugs, or deploy to cloud.

## Project structure

```
ds-job-agent/
├── agent.py          # Main agent
├── CLAUDE.md         # Claude Code instructions
├── requirements.txt  
├── .env.template     # Copy to .env and fill in keys
├── .gitignore        
├── reports/          # HTML reports (gitignored)
└── seen_jobs.json    # Seen job tracker (gitignored)
```

## Important

- `.env` is gitignored — your keys never go to GitHub
- This does NOT auto-apply — you always click Apply yourself
- Free RapidAPI tier = 500 req/month, enough for 3× daily

## License
MIT
