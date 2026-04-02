"""
DS Job Alert Agent
Searches Indeed UK, tailors resume & cover letter per job using Claude API,
produces an HTML report every 8 hours.
"""

import os, json, smtplib, requests, datetime, re
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import anthropic

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ── Config ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EMAIL_FROM        = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD    = os.getenv("EMAIL_PASSWORD")
EMAIL_TO          = os.getenv("EMAIL_TO")

SEEN_JOBS_FILE    = Path("seen_jobs.json")
REPORTS_DIR       = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

SEARCHES = [
    {"search": "Data Scientist",  "location": "United Kingdom"},
    {"search": "Data Analyst",    "location": "United Kingdom"},
    {"search": "Data Scientist",  "location": "remote"},
    {"search": "Data Analyst",    "location": "remote"},
]

MIN_SALARY = 55000  # filter out roles below this (where salary is shown)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Candidate profile (update this section with any changes) ───────────────────
CANDIDATE = {
    "name": "Deekshita Sridhar",
    "email": "deekshita15@gmail.com",
    "phone": "+44 7404 683609",
    "linkedin": "https://www.linkedin.com/in/deekshita-sridhar-89a80218a/",
    "github": "https://github.com/dsridhar2110",
    "portfolio": "https://www.deeksh.com",
    "location": "London, UK",
    "visa": "Valid UK Work Visa",

    "base_summary": """Data Scientist with 7 years of production software engineering experience 
and a Master of Data Science from Monash University (completed Jan 2026). Skilled in building 
predictive models, NLP pipelines, recommendation systems, and large-scale analytics workflows 
using Python, SQL, and PySpark. Combines deep engineering rigour with applied machine learning 
to deliver scalable, data-driven decision systems.""",

    "skills": {
        "Languages":        "Python, SQL (T-SQL, MySQL, Oracle), R, PySpark",
        "ML & AI":          "scikit-learn, PyTorch, XGBoost, NLP, Recommender Systems, Time-Series Forecasting, Statistical Modelling",
        "Data & Viz":       "Tableau, Power BI, R Shiny, ggplot2, Plotly, Streamlit",
        "Engineering":      "ReactJS, Vue 3, REST APIs, Git, Google Cloud, Amazon RDS, CI/CD",
        "Databases":        "Microsoft SQL Server, Oracle SQL, MySQL",
    },

    "experience": [
        {
            "title": "Lead ECM Developer",
            "company": "Ashghal (Public Works Authority)",
            "dates": "Apr 2019 – Dec 2023",
            "location": "Doha, Qatar",
            "bullets": [
                "Led development of PDLM — engineering Document Lifecycle Management platform with workflow automation and repository architecture",
                "Delivered platform for FIFA World Cup 2022, generating $1.5M in revenue; 3-week Agile delivery model with international teams",
                "Built full-stack system using ReactJS, jQuery, AJAX and Microsoft SQL; Python server-side logic and managerial dashboards",
            ]
        },
        {
            "title": "Lead Software Developer (OpenText)",
            "company": "Mannai Infotech",
            "dates": "Apr 2020 – Jun 2020",
            "location": "Doha, Qatar",
            "bullets": [
                "Built COVID-19 travel authorisation system using ReactJS, HTML5, CSS, Microsoft SQL and OpenText REST services on Google Cloud",
                "Delivered complete application within one month responding to pandemic-driven requirements",
            ]
        },
        {
            "title": "Software Developer (OpenText)",
            "company": "Qatar Cool",
            "dates": "Apr 2018 – Apr 2019",
            "location": "Doha, Qatar",
            "bullets": [
                "Developed contract management solution with reporting, workflow automation, renewal-based opportunity management and unified contract repository",
                "Promoted to lead technical developer after resolving complex production issues",
            ]
        },
        {
            "title": "Member of Technical Staff",
            "company": "Metricstream",
            "dates": "Jul 2015 – Jan 2018",
            "location": "Bengaluru, India",
            "bullets": [
                "Served clients Intel, PGE, BAE and Amedisys; maintained SQL Server stored procedures and Oracle SQL aggregations",
                "Executed two major upgrade projects contributing $200K additional revenue",
            ]
        },
    ],

    "projects": [
        {
            "name": "Fashion Image Recommendation System",
            "tech": "ResNet · PyTorch · DeepFashion",
            "dates": "Dec 2025 – Ongoing",
            "bullets": [
                "Built large-scale visual recommendation system on 289k+ labelled images using ResNet-based CNN",
                "Implemented nearest-neighbour search for content-based visual retrieval across 1,000 clothing attributes",
            ]
        },
        {
            "name": "NLP Text Classification & Topic Modelling",
            "tech": "scikit-learn · PyTorch · Gensim · Streamlit",
            "dates": "Oct 2025 – Dec 2025",
            "bullets": [
                "End-to-end pipeline on arXiv dataset: Logistic Regression, SVM, RNN, LSTM; LDA topic modelling",
                "Deployed Streamlit inference interface; visualised clusters with t-SNE and pyLDAvis",
            ]
        },
        {
            "name": "Amazon Hybrid Recommender System",
            "tech": "Python · SVD · TF-IDF",
            "dates": "Jul 2025 – Sep 2025",
            "bullets": [
                "Hybrid recommendation engine: SVD collaborative filtering + TF-IDF content-based; 100% prediction coverage",
            ]
        },
        {
            "name": "Spark Big Data Property Analysis",
            "tech": "PySpark · Spark SQL",
            "dates": "May 2025 – Jul 2025",
            "bullets": [
                "Distributed pipelines on 600MB+ dataset; benchmarked RDD, DataFrame, Spark SQL paradigms",
            ]
        },
    ],

    "education": [
        {"degree": "Master of Data Science", "school": "Monash University", "dates": "Feb 2024 – Jan 2026 (Completed)"},
        {"degree": "B.E. Information Science", "school": "PES Institute of Technology", "dates": "Sep 2011 – Jun 2015"},
    ]
}


# ── Indeed search (via RapidAPI or direct) ─────────────────────────────────────
def search_indeed(search_term: str, location: str) -> list[dict]:
    """Search Indeed UK for jobs. Returns list of job dicts."""
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
    print(f"  RAPIDAPI_KEY loaded: {'*' * (len(rapidapi_key) - 4)}{rapidapi_key[-4:]} (len={len(rapidapi_key)})")

    url = "https://indeed12.p.rapidapi.com/jobs/search"
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "indeed12.p.rapidapi.com"
    }
    params = {
        "query": search_term,
        "location": location,
        "page_id": "1",
        "country": "gb",
        "fromage": "1",  # last 1 day — we run every 8h so this catches everything
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 401:
            print(f"  401 Unauthorized — API key rejected. Response: {resp.text[:200]}")
            return []
        resp.raise_for_status()
        data = resp.json()
        return data.get("hits", [])
    except Exception as e:
        print(f"  Search error ({search_term} / {location}): {e}")
        return []


def fetch_job_details(job_id: str) -> dict:
    """Fetch full job details (description, url) for a single job ID."""
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "indeed12.p.rapidapi.com"
    }
    try:
        resp = requests.get(
            "https://indeed12.p.rapidapi.com/job/details",
            headers=headers,
            params={"job_id": job_id, "country": "gb"},
            timeout=15,
        )
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception as e:
        print(f"    Detail fetch error ({job_id}): {e}")
        return {}


def format_salary(salary_raw) -> str:
    """Return a human-readable salary string regardless of API format."""
    if not salary_raw:
        return "Salary not listed"
    if isinstance(salary_raw, str):
        return salary_raw
    if isinstance(salary_raw, dict):
        lo  = salary_raw.get("min") or salary_raw.get("minimum")
        hi  = salary_raw.get("max") or salary_raw.get("maximum")
        typ = salary_raw.get("type", "")
        period = {"YEARLY": "/ yr", "MONTHLY": "/ mo", "HOURLY": "/ hr"}.get(
            str(typ).upper(), str(typ))
        if lo and hi:
            return f"£{int(lo):,} – £{int(hi):,} {period}".strip()
        if hi:
            return f"Up to £{int(hi):,} {period}".strip()
        if lo:
            return f"From £{int(lo):,} {period}".strip()
    return str(salary_raw)


def load_seen_jobs() -> set:
    if SEEN_JOBS_FILE.exists():
        return set(json.loads(SEEN_JOBS_FILE.read_text()))
    return set()


def save_seen_jobs(seen: set):
    # Cap at 300 most-recent IDs so old entries don't permanently block jobs
    entries = list(seen)
    if len(entries) > 300:
        entries = entries[-300:]
    SEEN_JOBS_FILE.write_text(json.dumps(entries, indent=2))


def is_relevant(job: dict) -> bool:
    """Strict relevance filter — only Data Scientist / Data Analyst titles."""
    title = job.get("title", "").lower()

    # Must contain at least one of these core role keywords
    required_keywords = ["data scientist", "data analyst", "data science"]
    if not any(kw in title for kw in required_keywords):
        return False

    # Exclude seniority/role mismatches
    bad_words = ["junior", "graduate", "intern", "tutor", "trainer", "teaching",
                 "vice president", "vp ", "director", "head of", "manager",
                 "software engineer", "developer", "devops", "frontend", "backend"]
    if any(w in title for w in bad_words):
        return False

    # Salary filter where available
    salary_raw = job.get("salary", "")
    salary_str = salary_raw if isinstance(salary_raw, str) else str(salary_raw)
    m = re.findall(r"£([\d,]+)", salary_str)
    if m:
        amounts = [int(x.replace(",", "")) for x in m]
        if max(amounts) < MIN_SALARY:
            return False
    return True


# ── Claude API calls ───────────────────────────────────────────────────────────
def tailor_resume_summary(jd_text: str) -> str:
    """Ask Claude to rewrite the summary to match this specific JD."""
    prompt = f"""You are a professional resume writer. Here is a candidate's base summary:

{CANDIDATE['base_summary']}

Here is the job description they are applying for:

{jd_text[:3000]}

Rewrite the candidate's professional summary (3-4 sentences max) to best match this role.
- Keep it factual — only use details from the base summary above
- Mirror keywords from the JD naturally
- Do NOT add skills or experience they don't have
- Write in first person implied (no "I")
- Return ONLY the rewritten summary, no other text"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def generate_cover_letter(job_title: str, company: str, jd_text: str) -> str:
    """Generate a tailored cover letter for this specific role."""
    prompt = f"""Write a concise, professional cover letter for the following job application.

Candidate: {CANDIDATE['name']}
Applying for: {job_title} at {company}
Location: {CANDIDATE['location']}

Candidate background (use ONLY these facts):
- 7 years software engineering experience (ReactJS, SQL, REST APIs, cloud)
- MSc Data Science, Monash University (completed Jan 2026)
- Built: NLP pipeline (arXiv), hybrid recommender (289k images), PySpark big data pipeline (600MB+)
- Delivered $1.5M FIFA World Cup project; $200K DB optimisation projects
- Python, SQL, PyTorch, scikit-learn, PySpark, Tableau, Power BI
- Valid UK work visa, based in London

Job description:
{jd_text[:2500]}

Rules:
- 3 paragraphs only: (1) why this role, (2) most relevant experience for THIS role, (3) close
- Professional but warm tone
- Under 280 words total
- Do NOT use phrases like "I am writing to apply" or "Please find attached"
- Start directly with why you're excited about the role/company
- Return ONLY the cover letter text"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()


def highlight_skills_for_jd(jd_text: str) -> list[str]:
    """Return which of the candidate's skills are most relevant to this JD."""
    all_skills = []
    for skills in CANDIDATE["skills"].values():
        all_skills.extend([s.strip() for s in skills.split(",")])

    prompt = f"""From this list of skills: {", ".join(all_skills)}

Which 8-10 are most relevant to this job description? Return them as a comma-separated list only, no explanation.

Job description: {jd_text[:2000]}"""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}]
    )
    return [s.strip() for s in msg.content[0].text.split(",")]


# ── HTML report generator ──────────────────────────────────────────────────────
def generate_html_report(jobs_data: list[dict]) -> str:
    """Generate a clean HTML report with all jobs and tailored content."""
    now = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    count = len(jobs_data)

    job_cards = ""
    for i, j in enumerate(jobs_data, 1):
        skills_html = "".join(f'<span class="skill">{s}</span>' for s in j["highlighted_skills"])
        summary_escaped = j["tailored_summary"].replace("\n", "<br>")
        cover_escaped   = j["cover_letter"].replace("\n", "<br>")

        work_tags = ""
        for tag in j.get("work_tags", []):
            work_tags += f'<span class="work-tag">{tag}</span>'

        job_cards += f"""
        <div class="job-card" id="job-{i}">
          <div class="job-header">
            <div>
              <div class="job-title">{j['title']}</div>
              <div class="job-meta">{j['company']} · {j.get('location','United Kingdom')} · {j.get('salary','Salary not listed')}</div>
              <div class="job-meta" style="margin-top:4px">Posted: {j.get('date','—')} &nbsp;|&nbsp; Match score: <strong>{j.get('match','—')}</strong></div>
              {f'<div style="margin-top:6px">{work_tags}</div>' if work_tags else ''}
            </div>
            <a class="apply-btn" href="{j['url']}" target="_blank">Apply Now →</a>
          </div>
          <div class="tabs">
            <button class="tab-btn active" onclick="showTab(this,'summary-{i}')">Tailored Summary</button>
            <button class="tab-btn" onclick="showTab(this,'cover-{i}')">Cover Letter</button>
            <button class="tab-btn" onclick="showTab(this,'skills-{i}')">Key Skills</button>
            <button class="tab-btn" onclick="showTab(this,'jd-{i}')">Job Description</button>
          </div>
          <div id="summary-{i}" class="tab-content active">
            <div class="label">✦ Paste this as your resume summary for this application</div>
            <div class="content-box">{summary_escaped}</div>
            <button class="copy-btn" onclick="copyText('summary-{i}')">Copy Summary</button>
          </div>
          <div id="cover-{i}" class="tab-content">
            <div class="label">✦ Paste this as your cover letter — edit the greeting with the hiring manager's name if you know it</div>
            <div class="content-box">{cover_escaped}</div>
            <button class="copy-btn" onclick="copyText('cover-{i}')">Copy Cover Letter</button>
          </div>
          <div id="skills-{i}" class="tab-content">
            <div class="label">✦ Highlight these skills in your application — they match this JD best</div>
            <div style="margin-top:10px">{skills_html}</div>
          </div>
          <div id="jd-{i}" class="tab-content">
            <div class="content-box" style="font-size:13px;white-space:pre-wrap">{j.get('jd_text','Not available')[:3000]}</div>
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DS Job Alerts — {now}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f4f5f7; color: #1a1a2e; }}
  .header {{ background: #1F4E79; color: white; padding: 24px 32px; }}
  .header h1 {{ font-size: 22px; font-weight: 600; }}
  .header p {{ font-size: 14px; opacity: .8; margin-top: 4px; }}
  .container {{ max-width: 900px; margin: 24px auto; padding: 0 16px; }}
  .stats {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat {{ background: white; border-radius: 10px; padding: 14px 20px; flex: 1; min-width: 140px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .stat-num {{ font-size: 28px; font-weight: 600; color: #1F4E79; }}
  .stat-label {{ font-size: 12px; color: #666; margin-top: 2px; }}
  .job-card {{ background: white; border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .job-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; gap: 16px; }}
  .job-title {{ font-size: 17px; font-weight: 600; color: #1F4E79; }}
  .job-meta {{ font-size: 13px; color: #555; margin-top: 4px; }}
  .apply-btn {{ background: #1F4E79; color: white; padding: 10px 18px; border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 500; white-space: nowrap; flex-shrink: 0; }}
  .apply-btn:hover {{ background: #185FA5; }}
  .tabs {{ display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }}
  .tab-btn {{ padding: 6px 14px; border-radius: 16px; border: 1px solid #ddd; background: #f4f5f7; font-size: 12px; cursor: pointer; }}
  .tab-btn.active {{ background: #1F4E79; color: white; border-color: #1F4E79; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
  .label {{ font-size: 12px; color: #888; margin-bottom: 8px; }}
  .content-box {{ background: #f9f9fb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; font-size: 14px; line-height: 1.7; }}
  .copy-btn {{ margin-top: 10px; padding: 6px 16px; background: #e8f0fe; color: #1F4E79; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 500; }}
  .copy-btn:hover {{ background: #c7d7f7; }}
  .skill {{ display: inline-block; background: #EAF3DE; color: #3B6D11; border-radius: 12px; padding: 3px 10px; font-size: 12px; font-weight: 500; margin: 3px; }}
  .work-tag {{ display: inline-block; background: #EEF2FF; color: #3730A3; border-radius: 10px; padding: 2px 9px; font-size: 11px; font-weight: 500; margin: 2px; }}
  .footer {{ text-align: center; padding: 32px; font-size: 12px; color: #999; }}
</style>
</head>
<body>
<div class="header">
  <h1>DS Job Alerts — Deekshita Sridhar</h1>
  <p>Generated: {now} &nbsp;·&nbsp; {count} new roles found &nbsp;·&nbsp; Resume + cover letter tailored per job</p>
</div>
<div class="container">
  <div class="stats">
    <div class="stat"><div class="stat-num">{count}</div><div class="stat-label">New jobs this run</div></div>
    <div class="stat"><div class="stat-num">{count}</div><div class="stat-label">Tailored summaries ready</div></div>
    <div class="stat"><div class="stat-num">{count}</div><div class="stat-label">Cover letters ready</div></div>
  </div>
  {job_cards}
</div>
<div class="footer">Generated by DS Job Agent · Next run in 8 hours</div>
<script>
function showTab(btn, id) {{
  const card = btn.closest('.job-card');
  card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  card.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(id).classList.add('active');
}}
function copyText(id) {{
  const el = document.getElementById(id).querySelector('.content-box');
  navigator.clipboard.writeText(el.innerText).then(() => {{
    const btn = document.getElementById(id).querySelector('.copy-btn');
    const orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = orig, 2000);
  }});
}}
</script>
</body>
</html>"""


# ── Email sender ───────────────────────────────────────────────────────────────
def send_status_email():
    """Send a brief status email when the agent ran but found no new jobs."""
    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg["Subject"] = f"DS Job Agent ran — no new jobs {datetime.datetime.now().strftime('%d %b %H:%M')}"
        msg.attach(MIMEText(
            "Hi Deekshita,\n\nYour job agent ran this cycle but found no new Data Scientist / "
            "Data Analyst roles that haven't been seen before.\n\nThe agent is healthy and will "
            "check again in 8 hours.\n\n— Your Job Agent", "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"  Status email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"  Status email error: {e}")


def send_email(report_path: Path, job_count: int):
    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        missing = [k for k, v in {"EMAIL_FROM": EMAIL_FROM, "EMAIL_PASSWORD": EMAIL_PASSWORD, "EMAIL_TO": EMAIL_TO}.items() if not v]
        print(f"  ⚠ Email skipped — missing .env values: {', '.join(missing)}")
        print("  → Add these to your .env file to receive email alerts")
        return
    print(f"  Sending email from {EMAIL_FROM} → {EMAIL_TO}")
    try:
        msg = MIMEMultipart()
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg["Subject"] = f"🔔 {job_count} new DS jobs — {datetime.datetime.now().strftime('%d %b %H:%M')}"
        body = f"""Hi Deekshita,

Found {job_count} new Data Science roles in London this run.

Each job has:
✓ Tailored resume summary (copy-paste ready)
✓ Personalised cover letter
✓ Key skills highlighted for this JD
✓ Direct apply link

Open the attached HTML file in your browser to review and apply.

Good luck!
— Your Job Agent"""
        msg.attach(MIMEText(body, "plain"))
        with open(report_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={report_path.name}")
            msg.attach(part)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"  Email sent to {EMAIL_TO}")
    except Exception as e:
        print(f"  Email error: {e}")


# ── Main run ───────────────────────────────────────────────────────────────────
def run():
    print(f"\n{'='*60}")
    print(f"DS Job Agent — {datetime.datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'='*60}")

    seen = load_seen_jobs()
    new_jobs = []

    for search_cfg in SEARCHES:
        print(f"\nSearching: {search_cfg['search']} in {search_cfg['location']}...")
        results = search_indeed(search_cfg["search"], search_cfg["location"])
        print(f"  Found {len(results)} results")

        for job in results:
            job_id = job.get("id") or job.get("jobkey", "")
            if job_id in seen:
                continue
            if not is_relevant(job):
                print(f"  Skipped (filtered): {job.get('title','?')}")
                continue
            seen.add(job_id)
            new_jobs.append(job)
            print(f"  New job: {job.get('title','?')} @ {job.get('company','?')}")

    if not new_jobs:
        print("\nNo new jobs this run — sending status email.")
        save_seen_jobs(seen)
        send_status_email()
        return

    print(f"\nProcessing {len(new_jobs)} new jobs with Claude...")
    jobs_data = []

    for job in new_jobs:
        title   = job.get("title", "Data Scientist")
        company = job.get("company", "")
        date    = job.get("date") or ""

        # Fetch full job details to get description and canonical URL
        job_id  = job.get("id") or job.get("jobkey", "")
        print(f"  Fetching details: {title} @ {company}")
        details = fetch_job_details(job_id) if job_id else {}

        # Description: details endpoint is authoritative; fall back to search snippet
        jd_text = (details.get("description")
                   or details.get("job_description")
                   or details.get("full_description")
                   or job.get("description")
                   or job.get("snippet")
                   or "")

        # URL: prefer the detail response, then search hit, then construct from job_id
        url = (details.get("link") or details.get("url") or details.get("job_url")
               or job.get("link") or job.get("url")
               or (f"https://uk.indeed.com/viewjob?jk={job_id}" if job_id else "#"))

        # Salary: merge search + detail, format nicely
        salary_raw = (details.get("salary") or job.get("salary")
                      or job.get("formattedRelativeTime") or "")
        salary = format_salary(salary_raw)

        # Work-setting tags
        work_tags = []
        raw_tags = (details.get("jobTypes") or details.get("workTypes")
                    or job.get("jobTypes") or job.get("attributes") or [])
        if isinstance(raw_tags, list):
            work_tags = [str(t) for t in raw_tags]
        jd_lower = jd_text.lower()
        for kw, label in [("hybrid", "Hybrid"), ("in-person", "In-person"),
                           ("on-site", "On-site"), ("remote", "Remote"),
                           ("flexitime", "Flexitime"), ("flexible hours", "Flexitime"),
                           ("flexible working", "Flexible working")]:
            if kw in jd_lower and label not in work_tags:
                work_tags.append(label)

        if not jd_text:
            print(f"    ⚠ No job description retrieved — tailoring will be generic")

        print(f"  Tailoring for: {title} @ {company}")
        try:
            tailored_summary    = tailor_resume_summary(jd_text)
            cover_letter        = generate_cover_letter(title, company, jd_text)
            highlighted_skills  = highlight_skills_for_jd(jd_text)
        except Exception as e:
            print(f"    Claude API error: {e}")
            tailored_summary   = CANDIDATE["base_summary"]
            cover_letter       = "Cover letter generation failed — check API key"
            highlighted_skills = []

        jobs_data.append({
            "title":             title,
            "company":           company,
            "location":          job.get("location", "United Kingdom"),
            "work_tags":         work_tags,
            "salary":            salary,
            "date":              date,
            "url":               url,
            "jd_text":           jd_text,
            "tailored_summary":  tailored_summary,
            "cover_letter":      cover_letter,
            "highlighted_skills": highlighted_skills,
            "match":             f"{min(95, 65 + len(highlighted_skills) * 3)}%" if highlighted_skills else "—",
        })

    # Generate report
    html = generate_html_report(jobs_data)
    ts   = datetime.datetime.now().strftime("%Y-%m-%d_%H")
    report_path = REPORTS_DIR / f"report_{ts}.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"\n✓ Report saved: {report_path}")

    # Open in browser automatically
    import webbrowser
    webbrowser.open(str(report_path.resolve()))

    # Send email
    send_email(report_path, len(jobs_data))

    save_seen_jobs(seen)
    print(f"\n✓ Done. {len(jobs_data)} jobs processed. Next run in 8 hours.")


# ── Scheduler ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import schedule, time
    run()  # Run immediately on start
    schedule.every(8).hours.do(run)
    print("\nAgent running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)
