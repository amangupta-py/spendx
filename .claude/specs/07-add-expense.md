# Spec: Add Expense

## Overview
Step 7 implements the "Add Expense" feature, allowing logged-in users to record
a new expense via a form at `/expenses/add`. This is the first write path for
expense data — the form collects amount, category, date, and an optional
description, then inserts a row into the `expenses` table. On success a pop of expense added should appear and the user is redirected to the profile page where the new expense appears immediately.

## Depends on
- Step 1: Database setup (`expenses` table exists with correct schema)
- Step 2: Registration (users stored in DB)
- Step 3: Login / Logout (`session["user_id"]` set on login)
- Step 4: Profile page design (redirect destination after add)
- Step 5: Backend routes for profile page (profile page renders expenses)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert a new expense, redirect to `/profile` — logged-in only

## Database changes
No database changes. The `expenses` table already exists with the required
columns: `user_id`, `amount`, `category`, `date`, `description`.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Form with `method="POST"` and `action="/expenses/add"`
  - Fields: `amount` (number, step 0.01, required), `category` (select,
    required), `date` (date input, required, defaults to today), `description`
    (textarea, optional)
  - Category options: Food, Transport, Bills, Health, Entertainment, Shopping, Other
  - Submit button and a cancel link back to `/profile`
  - `{% if error %}` block to display validation errors above the form

## Files to change
- `app.py` — replace the stub `add_expense` route with a full GET/POST handler:
  - GET: render `add_expense.html`, pre-populate `date` with today's date
  - POST: read and validate form fields, call `create_expense()`, redirect to `/profile`
  - Both methods: require `session["user_id"]`, redirect to `/login` if not set

## Files to create
- `templates/add_expense.html` — the add-expense form template
- `database/expense_queries.py` — `create_expense(user_id, amount, category, date, description)` helper

  Alternatively, `create_expense` may be added to `database/db.py` if the team
  prefers a single module; either location is acceptable as long as it is
  imported correctly in `app.py`.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (not relevant here but must not be broken)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `amount` must be validated as a positive float server-side; reject ≤ 0
- `date` must be validated as a valid `YYYY-MM-DD` string server-side
- `category` must be one of the allowed values server-side (whitelist check)
- On any validation failure, re-render the form with the `error` message and
  the previously submitted values pre-populated (do not lose the user's input)
- The route must be unreachable without a valid session — redirect to `/login`
- Do not use `flash()` for the inline form error; use the `{% if error %}` pattern
- Add the `Add Expense` button in `Recent Transaction` section at right top corner and should match the website theme and font.

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders the form with today's date pre-filled
- [ ] Submitting the form with all valid fields inserts a row in `expenses` and redirects to `/profile`
- [ ] The new expense appears in the transaction list on the profile page immediately after redirect
- [ ] Submitting with a missing or zero/negative amount re-renders the form with an error message
- [ ] Submitting with an invalid or missing date re-renders the form with an error message
- [ ] Submitting with an invalid category re-renders the form with an error message
- [ ] On validation failure, previously entered values are pre-populated in the form
- [ ] The cancel link returns the user to `/profile` without inserting any data
