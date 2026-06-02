# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run development server (port 5001, debug mode)
python app.py

# Run tests
pytest

# Run a single test file
pytest tests/test_app.py

# Install dependencies (activate venv first)
pip install -r requirements.txt
```

## Architecture

**Spendly** is a Flask + SQLite expense tracker built as a student learning scaffold. The backend is intentionally partially implemented — database logic and form handlers are stubs students fill in.

### Structure

```
app.py          # All Flask routes and app factory
database/
  db.py         # SQLite connection, init_db(), seed_db() — partially stubbed
templates/
  base.html     # Layout with navbar/footer; all pages extend this
  landing.html  # Marketing homepage (fully implemented)
  login.html    # Auth form with {% if error %} block
  register.html # Auth form with {% if error %} block
static/
  css/style.css # Unified stylesheet using CSS custom properties
  js/main.js    # Minimal vanilla JS (landing modal only)
```

### Key patterns

- **All routes live in `app.py`** — Flask decorators, no blueprints.
- **Template inheritance** — every page extends `base.html` and fills `{% block content %}`.
- **Database** — SQLite via Python's `sqlite3` module; `database/db.py` holds `get_db()`, `init_db()`, and `seed_db()`. The DB file (`expense_tracker.db`) is gitignored.
- **Error display** — forms use `{% if error %}` context variables passed from route handlers.
- **No frontend framework** — vanilla HTML/CSS/JS only. Modal on landing page is the only JS interaction.

### Design tokens (CSS custom properties on `:root`)

| Variable | Value | Use |
|---|---|---|
| `--ink` | `#0f0f0f` | Primary text |
| `--paper` | `#f7f6f3` | Page background |
| `--green` | `#1a472a` | Primary accent |
| `--orange` | `#c17f24` | Secondary accent |

Fonts: **DM Serif Display** (headings) and **DM Sans** (body) — loaded from Google Fonts in `base.html`.

### Unimplemented areas (student scaffolds)

Routes in `app.py` that are stubs: logout, profile, add/edit/delete expense. The database schema (tables, constraints) and all `INSERT`/`SELECT`/`UPDATE`/`DELETE` queries in `database/db.py` are also left for students to implement.
