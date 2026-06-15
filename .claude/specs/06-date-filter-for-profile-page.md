# Spec: Date Filter For Profile Page

## Overview
Step 6 adds a date-range filter to the profile page so users can narrow all
four data sections — summary stats, transaction history, category breakdown,
and top category — to a specific time window. Currently the profile page always
shows all-time data. This step introduces a date picker UI (month/year start
and end selectors) that submits as a GET form, and updates the backend queries
to accept optional `start_date` / `end_date` parameters. When no filter is
set, the page behaves exactly as before (all-time view).

## Depends on
- Step 1: Database setup (`expenses` table with `date` column exists)
- Step 2: Registration (users stored in DB)
- Step 3: Login / Logout (`session["user_id"]` set on login)
- Step 4: Profile page design (template structure in place)
- Step 5: Backend routes for profile page (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown`, `get_user_by_id` all implemented)

## Routes
- `GET /profile` — extended to accept optional query params `start_date` and
  `end_date` (format `YYYY-MM-DD`). Access: logged-in only.

No new routes.

## Database changes
No database changes. The `expenses.date` column (`TEXT NOT NULL`, stored as
`YYYY-MM-DD`) already supports range filtering with SQL `BETWEEN`.

## Templates
- **Modify**: `templates/profile.html`
  - Add a date filter bar above the stats section with two `<input type="month">` fields (`start_date`, `end_date`) inside a `<form method="GET" action="/profile">`.
  - Add a "Filter" submit button and a "Clear" link that resets to `/profile`.
  - Display the active filter range as a human-readable label when a filter is applied (e.g. "Jun 2026 – Jun 2026").
  - All four data sections already loop over template variables — no structural changes needed beyond the new filter bar.

## Files to change
- `app.py` — read `start_date` and `end_date` from `request.args`, validate
  format, pass them through to all four query helpers.
- `database/queries.py` — update `get_summary_stats`, `get_recent_transactions`,
  and `get_category_breakdown` to accept optional `start_date` / `end_date`
  keyword arguments and add a `WHERE date BETWEEN ? AND ?` clause when provided.
  `get_user_by_id` does not need date filtering.
- `templates/profile.html` — add the filter bar UI.
- `static/css/style.css` — add styles for the filter bar (`.profile-filter-bar`,
  `.profile-filter-label`, `.btn-filter`, `.btn-clear`).

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles (the `style="width: {{ c.pct }}%"` on bar fills is
  pre-existing and acceptable; do not add new inline styles)
- Date inputs use `type="month"` (renders as `YYYY-MM`); convert to
  `YYYY-MM-01` (start) and `YYYY-MM-<last-day>` (end) in the route before
  passing to queries — never rely on the browser for this conversion
- When `start_date` or `end_date` is missing or malformed, silently fall back
  to all-time view (no 400 error shown to the user)
- The "Clear" link must be a plain `<a href="/profile">` — not a form submit
- Filter state must survive a page reload: pre-populate the month inputs with
  the currently active filter values from `request.args`
- `get_recent_transactions` filter must respect the existing `limit` parameter
  alongside the date range

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data (unchanged behaviour)
- [ ] Selecting a start month and end month and clicking "Filter" reloads the page with `?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` in the URL
- [ ] Total spent, transaction count, top category, transaction list, and category breakdown all reflect only the filtered date range
- [ ] The month inputs are pre-populated with the active filter after submitting
- [ ] An active filter shows a human-readable label (e.g. "Jun 2026 – Jun 2026")
- [ ] Clicking "Clear" removes all filter params and restores all-time data
- [ ] Submitting with only one date field filled in falls back to all-time view gracefully (no crash, no error page)
- [ ] A user with no expenses in the filtered range sees ₹0.00 total, 0 transactions, empty breakdown — no errors
