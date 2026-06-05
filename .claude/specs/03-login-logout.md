# Spec: Login and Logout

## Overview
Implement session-based login and logout so registered users can authenticate and access protected areas of Spendly. The `POST /login` route validates credentials against the database, sets a session cookie on success, and redirects to the dashboard stub. The `GET /logout` route clears the session and redirects to the landing page. This step introduces Flask session management and the access-control pattern that all future protected routes will follow.

## Depends on
- Step 01 — Database Setup (`users` table with `email` and `password_hash` columns must exist)
- Step 02 — Registration (at least one user row must be present to test login)

## Routes
- `GET /login` — render the login form — public (already exists as stub, needs POST added)
- `POST /login` — validate credentials, set session, redirect to `/dashboard` — public
- `GET /logout` — clear session, redirect to `/` — logged-in (currently a stub returning a string)

## Database changes
No database changes. The existing `users` table is queried with a `SELECT` by email; `password_hash` is verified with `werkzeug.security.check_password_hash`. No new tables or columns are needed.

## Templates
- **Modify:** `templates/login.html` — add `method="POST"` and `action="/login"` to the `<form>` tag; ensure `email` and `password` input fields have the correct `name` attributes; display `{% if error %}` block for invalid-credentials errors; display `{% with messages = get_flashed_messages() %}` block to show the registration success flash.

## Files to change
- `app.py` — convert `/login` from GET-only stub to GET+POST; implement credential lookup and session write; implement `/logout` to clear session and redirect
- `database/db.py` — add `get_user_by_email(email)` helper that returns a `sqlite3.Row` or `None`
- `templates/login.html` — wire up form attributes, error display, and flash message display

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is already available via the existing Werkzeug install.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Store only `user_id` and `user_name` in `session` — never store the password hash or full row
- After successful login set `session["user_id"]` and `session["user_name"]`, then redirect to `url_for("dashboard")` (the placeholder route at `/dashboard` will be a stub for now)
- Show a single generic error on bad credentials ("Invalid email or password.") — do not reveal which field was wrong
- `/logout` must call `session.clear()` (not `session.pop`) and redirect to `url_for("landing")`
- Do not add a `/dashboard` route in this step — the redirect target can remain the existing stub or be a minimal "Dashboard coming soon" string response added inline
- After login in, i should not be able to use `/login` and `/register`

## Definition of done
- [ ] `GET /login` renders the login form without errors
- [ ] Flash message from registration ("Account created! Please sign in.") is visible on the login page after redirect from `/register`
- [ ] Submitting correct email and password sets a session and redirects away from `/login`
- [ ] Submitting an unrecognised email shows "Invalid email or password." inline and does not set a session
- [ ] Submitting a wrong password for a valid email shows "Invalid email or password." inline and does not set a session
- [ ] Submitting with empty fields shows an inline error and does not query the database
- [ ] `GET /logout` clears the session and redirects to the landing page (`/`)
- [ ] After logout, navigating back to `/login` does not show a logged-in state
- [ ] App starts and seeds without errors after this change
