# 📚 StudyFlow — Study Planner Web App

A full-featured, production-ready study planner built with Flask + SQLite.

## Features

- **Auth** — Register, login with hashed passwords (Werkzeug)
- **Tasks** — Add, prioritize, complete, delete with subject tagging
- **Goals** — Set hour targets with visual progress bars
- **Study Sessions** — Log sessions (auto-updates goal progress)
- **Subjects** — Color-coded subject management
- **Reminders** — Overdue task notification system
- **Dashboard** — Weekly activity chart, subject breakdown, stats

## Setup

```bash
# 1. Clone / download the project
cd study_planner

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Project Structure

```
study_planner/
├── app.py                  # Flask backend (all routes + DB logic)
├── study_planner.db        # SQLite database (auto-created)
├── requirements.txt
├── static/
│   ├── style.css           # Full design system
│   └── app.js              # Interactivity + canvas chart
└── templates/
    ├── base.html           # Sidebar layout shell
    ├── login.html
    ├── register.html
    └── dashboard.html      # Main dashboard
```

## Tech Stack

- **Backend**: Python 3.10+, Flask 3, Flask-Login, Werkzeug
- **Database**: SQLite (zero-config, file-based)
- **Frontend**: Vanilla HTML/CSS/JS, Google Fonts (Syne + DM Sans)
- **Charts**: Custom Canvas API (no external JS libs)

## Production Deployment

For production, replace `app.secret_key` with a strong random key and set `debug=False`.
Use Gunicorn + Nginx or deploy to Railway / Render / Heroku.

```bash
pip install gunicorn
gunicorn -w 4 app:app
```
