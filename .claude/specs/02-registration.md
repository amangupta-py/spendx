# Spec: Registration

## Overview
Implement user registration so new visitors can create a Spendly account. This step wires up the `POST /register` route to validate form input, check for duplicate emails, hash the password, insert a new row into the `users` table, show the successful message and then redirect to login on success. It is the first feature that writes user-generated data to the database and establishes the pattern all future write routes will follow.

## Depends on
- Step 01 — Database Setup (`users` table must exist)

## Routes
- `GET /register` — render the registration form — public (already exists as stub)
- `POST /register` — validate input, create user, redirect to `/login` — public

## Database changes
No new tables or columns. The `users` table created in Step 01 is used as-is:
- `name` TEXT NOT NULL
- `email` TEXT UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL
- `created_at` TEXT DEFAULT (datetime('now'))

## Templates
- **Modify:** `templates/register.html` — add `method="POST"` and `action="/register"` to the `<form>` tag; ensure `name`, `email`, `password`, and `confirm_password` input fields are present with correct `name` attributes; display `{% if error %}` block for validation errors.

## Files to change
- `app.py` — add `POST` method to `/register` route; import `session` and `redirect` and `url_for` from flask; add `request` import; implement registration logic
- `database/db.py` — add `create_user(name, email, password_hash)` helper function
- `templates/register.html` — wire up form attributes and error display

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Catch `sqlite3.IntegrityError` to detect duplicate email and show a user-friendly error message
- Validate server-side: name not empty, email not empty, password not empty, password == confirm_password
- Do not log the user in after registration — redirect to `/login` with a success message or just the login page
- `app.secret_key` must be set for `session` to work (add a hard-coded dev key for now)

## Definition of done
- [ ] `GET /register` renders the registration form without errors
- [ ] Submitting the form with all valid fields creates a new row in `users` and redirects to `/login`
- [ ] Submitting with mismatched passwords shows an inline error and does not insert a row
- [ ] Submitting with an already-registered email shows an inline error and does not insert a duplicate row
- [ ] Submitting with any empty field shows an inline error
- [ ] Password is stored as a hash (not plaintext) — verifiable by inspecting the DB
- [ ] App starts and seeds without errors after this change
