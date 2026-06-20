"""
Tests for Step 7: Add Expense

Spec: .claude/specs/07-add-expense.md

Coverage:
  1.  Auth guard GET  — unauthenticated GET /expenses/add → 302 /login
  2.  Auth guard POST — unauthenticated POST /expenses/add → 302 /login
  3.  GET happy path  — authenticated GET returns 200 and renders the form
  4.  GET today's date pre-filled in the date input
  5.  GET template landmarks — cancel link, field names, submit button present
  6.  POST happy path — valid data → 302 redirect to /profile
  7.  DB side effect  — after valid POST the expense row is in the DB
  8.  Flash message   — "Expense added successfully!" appears after redirect
  9.  Amount = 0      → re-renders with error, no DB insert
  10. Negative amount → re-renders with error, no DB insert
  11. Blank amount    → re-renders with error, no DB insert
  12. Non-numeric amount → re-renders with error, no DB insert
  13. Invalid date string → re-renders with error, no DB insert
  14. Missing/blank date → re-renders with error, no DB insert
  15. Invalid category   → re-renders with error, no DB insert
  16. Value preservation — submitted fields echo back into form on error
  17. Valid POST without description → inserts NULL description
  18. Parametrized invalid amounts
  19. Parametrized all valid categories succeed
  20. Parametrized invalid categories are rejected

Fixture strategy:
  - monkeypatch database.db.DB_PATH to a tmp_path file per test so the
    real spendly.db is never touched.
  - A seed user is inserted so the foreign-key constraint on expenses.user_id
    is satisfied.
  - Authenticated sessions are set via client.session_transaction() with
    user_id and user_name — no login form needed.
"""

import sqlite3
from datetime import date

import pytest

import database.db as db_module
from database.db import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_test_user(db_path: str) -> int:
    """Insert a minimal test user and return its id."""
    from werkzeug.security import generate_password_hash
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Test User", "test@spendly.com", generate_password_hash("testpass")),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def _count_expenses(db_path: str, user_id: int) -> int:
    """Return the number of expense rows for the given user."""
    conn = sqlite3.connect(db_path)
    count = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def _fetch_latest_expense(db_path: str, user_id: int) -> dict | None:
    """Return the most recently inserted expense row for a user as a dict."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """
    Provide a fresh, empty (schema-only) SQLite database.
    Monkeypatches DB_PATH so no real DB is touched.
    Returns the path string to the temp db file.
    """
    tmp_db = tmp_path / "test_spendly.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_db))
    init_db()
    return str(tmp_db)


@pytest.fixture()
def auth_client(fresh_db):
    """
    Flask test client backed by a fresh temp DB with one test user
    pre-loaded in the session.  Returns (client, user_id, db_path).
    """
    from app import app as flask_app

    user_id = _insert_test_user(fresh_db)

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = "Test User"
        yield c, user_id, fresh_db


@pytest.fixture()
def anon_client(fresh_db):
    """Flask test client with NO session — simulates a logged-out user."""
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Auth guard — GET while logged out
# ---------------------------------------------------------------------------

def test_add_expense_logged_out_get_redirects_to_login(anon_client):
    """GET /expenses/add without a session must redirect to /login."""
    response = anon_client.get("/expenses/add")
    assert response.status_code == 302, (
        f"Expected 302 for unauthenticated GET, got {response.status_code}"
    )
    assert "/login" in response.headers["Location"], (
        "Expected redirect target to contain '/login'"
    )


# ---------------------------------------------------------------------------
# 2. Auth guard — POST while logged out
# ---------------------------------------------------------------------------

def test_add_expense_logged_out_post_redirects_to_login(anon_client):
    """POST /expenses/add without a session must redirect to /login."""
    response = anon_client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": "2026-06-20",
        "description": "Lunch",
    })
    assert response.status_code == 302, (
        f"Expected 302 for unauthenticated POST, got {response.status_code}"
    )
    assert "/login" in response.headers["Location"], (
        "Expected redirect target to contain '/login'"
    )


# ---------------------------------------------------------------------------
# 3. GET happy path — renders the form
# ---------------------------------------------------------------------------

def test_add_expense_get_authenticated_returns_200(auth_client):
    """Authenticated GET /expenses/add must return HTTP 200."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    assert response.status_code == 200, (
        f"Expected 200 for authenticated GET /expenses/add, got {response.status_code}"
    )


def test_add_expense_get_renders_form_title(auth_client):
    """The rendered page must contain 'Add Expense' text."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    assert b"Add Expense" in response.data, (
        "Expected 'Add Expense' heading in the rendered form page"
    )


# ---------------------------------------------------------------------------
# 4. GET — today's date pre-filled
# ---------------------------------------------------------------------------

def test_add_expense_get_prepopulates_todays_date(auth_client):
    """The date input must be pre-populated with today's date in YYYY-MM-DD format."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    today_str = date.today().isoformat()
    assert today_str.encode() in response.data, (
        f"Expected today's date {today_str!r} to be present in the form HTML"
    )


# ---------------------------------------------------------------------------
# 5. GET template landmarks
# ---------------------------------------------------------------------------

def test_add_expense_get_has_cancel_link_to_profile(auth_client):
    """The form page must include a link back to /profile."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    html = response.data.decode("utf-8")
    assert "/profile" in html, (
        "Expected a cancel/back link to '/profile' in the add-expense form"
    )


def test_add_expense_get_has_amount_input(auth_client):
    """The form must contain an input named 'amount'."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    assert b'name="amount"' in response.data, (
        "Expected input field with name='amount' in the form"
    )


def test_add_expense_get_has_category_select(auth_client):
    """The form must contain a select named 'category'."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    assert b'name="category"' in response.data, (
        "Expected select field with name='category' in the form"
    )


def test_add_expense_get_has_date_input(auth_client):
    """The form must contain an input named 'date'."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    assert b'name="date"' in response.data, (
        "Expected input field with name='date' in the form"
    )


def test_add_expense_get_has_description_textarea(auth_client):
    """The form must contain a textarea named 'description'."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    assert b'name="description"' in response.data, (
        "Expected textarea with name='description' in the form"
    )


def test_add_expense_get_has_all_seven_categories(auth_client):
    """The category select must list all 7 allowed categories."""
    client, user_id, db_path = auth_client
    response = client.get("/expenses/add")
    html = response.data.decode("utf-8")
    for cat in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
        assert cat in html, (
            f"Expected category option '{cat}' in the category select"
        )


# ---------------------------------------------------------------------------
# 6. POST happy path — redirect to /profile
# ---------------------------------------------------------------------------

def test_add_expense_valid_post_redirects_to_profile(auth_client):
    """A valid POST must redirect (302) to /profile."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "25.50",
        "category": "Food",
        "date": "2026-06-20",
        "description": "Lunch at cafe",
    })
    assert response.status_code == 302, (
        f"Expected 302 redirect after valid POST, got {response.status_code}"
    )
    assert "/profile" in response.headers["Location"], (
        "Expected redirect target to contain '/profile'"
    )


# ---------------------------------------------------------------------------
# 7. DB side effect — row inserted after valid POST
# ---------------------------------------------------------------------------

def test_add_expense_valid_post_inserts_row_in_db(auth_client):
    """After a valid POST the expenses table must contain one new row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)

    client.post("/expenses/add", data={
        "amount": "25.50",
        "category": "Food",
        "date": "2026-06-20",
        "description": "Lunch at cafe",
    })

    after = _count_expenses(db_path, user_id)
    assert after == before + 1, (
        f"Expected one new expense row in DB, before={before}, after={after}"
    )


def test_add_expense_valid_post_correct_amount_stored(auth_client):
    """The inserted row's amount must match the submitted value."""
    client, user_id, db_path = auth_client
    client.post("/expenses/add", data={
        "amount": "99.99",
        "category": "Bills",
        "date": "2026-06-15",
        "description": "Electric bill",
    })
    row = _fetch_latest_expense(db_path, user_id)
    assert row is not None, "Expected at least one expense row in the DB"
    assert abs(row["amount"] - 99.99) < 0.001, (
        f"Expected amount 99.99, got {row['amount']}"
    )


def test_add_expense_valid_post_correct_category_stored(auth_client):
    """The inserted row's category must match the submitted value."""
    client, user_id, db_path = auth_client
    client.post("/expenses/add", data={
        "amount": "50.00",
        "category": "Health",
        "date": "2026-06-10",
        "description": "Doctor visit",
    })
    row = _fetch_latest_expense(db_path, user_id)
    assert row is not None
    assert row["category"] == "Health", (
        f"Expected category 'Health', got {row['category']!r}"
    )


def test_add_expense_valid_post_correct_date_stored(auth_client):
    """The inserted row's date must match the submitted YYYY-MM-DD value."""
    client, user_id, db_path = auth_client
    client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Other",
        "date": "2026-05-01",
        "description": "",
    })
    row = _fetch_latest_expense(db_path, user_id)
    assert row is not None
    assert row["date"] == "2026-05-01", (
        f"Expected date '2026-05-01', got {row['date']!r}"
    )


def test_add_expense_valid_post_correct_user_id_stored(auth_client):
    """The inserted row's user_id must match the session's user_id."""
    client, user_id, db_path = auth_client
    client.post("/expenses/add", data={
        "amount": "12.00",
        "category": "Transport",
        "date": "2026-06-18",
        "description": "Bus fare",
    })
    row = _fetch_latest_expense(db_path, user_id)
    assert row is not None
    assert row["user_id"] == user_id, (
        f"Expected user_id={user_id}, got {row['user_id']}"
    )


# ---------------------------------------------------------------------------
# 8. Flash message after successful POST
# ---------------------------------------------------------------------------

def test_add_expense_valid_post_flash_message_on_profile(auth_client):
    """After a valid POST, following the redirect to /profile must show the flash message."""
    client, user_id, db_path = auth_client
    response = client.post(
        "/expenses/add",
        data={
            "amount": "25.00",
            "category": "Shopping",
            "date": "2026-06-20",
            "description": "New book",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200, (
        f"Expected 200 after following redirect to /profile, got {response.status_code}"
    )
    assert b"Expense added successfully" in response.data, (
        "Expected flash message 'Expense added successfully!' on profile page after add"
    )


# ---------------------------------------------------------------------------
# 9. Amount = 0 → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_amount_zero_returns_200_with_error(auth_client):
    """Submitting amount=0 must re-render the form (200) with an error message."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for amount=0, got {response.status_code}"
    )
    assert b"error" in response.data.lower() or b"positive" in response.data.lower(), (
        "Expected an error message about amount when submitting amount=0"
    )


def test_add_expense_amount_zero_does_not_insert(auth_client):
    """Submitting amount=0 must not create a new expense row in the DB."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for amount=0, but count changed from {before} to {after}"
    )


# ---------------------------------------------------------------------------
# 10. Negative amount → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_negative_amount_returns_200_with_error(auth_client):
    """Submitting a negative amount must re-render the form with an error."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "-5.00",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for negative amount, got {response.status_code}"
    )
    assert b"error" in response.data.lower() or b"positive" in response.data.lower(), (
        "Expected an error message when submitting a negative amount"
    )


def test_add_expense_negative_amount_does_not_insert(auth_client):
    """Submitting a negative amount must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "-5.00",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for negative amount, count changed {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 11. Blank/missing amount → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_blank_amount_returns_200_with_error(auth_client):
    """Submitting an empty amount string must re-render the form with an error."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for blank amount, got {response.status_code}"
    )
    html = response.data.decode("utf-8")
    assert "error" in html.lower() or "positive" in html.lower(), (
        "Expected an error message for blank amount"
    )


def test_add_expense_blank_amount_does_not_insert(auth_client):
    """Submitting an empty amount must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for blank amount, count changed {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 12. Non-numeric amount → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_nonnumeric_amount_returns_200_with_error(auth_client):
    """Submitting a non-numeric amount must re-render the form with an error."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for non-numeric amount, got {response.status_code}"
    )
    assert b"error" in response.data.lower() or b"positive" in response.data.lower(), (
        "Expected an error message for non-numeric amount"
    )


def test_add_expense_nonnumeric_amount_does_not_insert(auth_client):
    """Submitting a non-numeric amount must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "abc",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for non-numeric amount, count changed {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 13. Invalid date string → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_invalid_date_string_returns_200_with_error(auth_client):
    """Submitting a malformed date must re-render the form with an error."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": "not-a-date",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for invalid date, got {response.status_code}"
    )
    html = response.data.decode("utf-8")
    assert "error" in html.lower() or "valid date" in html.lower(), (
        "Expected an error message for an invalid date string"
    )


def test_add_expense_invalid_date_string_does_not_insert(auth_client):
    """An invalid date string must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": "not-a-date",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for invalid date, count changed {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 14. Missing/blank date → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_blank_date_returns_200_with_error(auth_client):
    """Submitting an empty date must re-render the form with an error."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": "",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for blank date, got {response.status_code}"
    )
    html = response.data.decode("utf-8")
    assert "error" in html.lower() or "valid date" in html.lower(), (
        "Expected an error message for a blank date"
    )


def test_add_expense_blank_date_does_not_insert(auth_client):
    """A blank date must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Food",
        "date": "",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for blank date, count changed {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 15. Invalid category → error, no insert
# ---------------------------------------------------------------------------

def test_add_expense_invalid_category_returns_200_with_error(auth_client):
    """Submitting a category not in the whitelist must re-render the form with an error."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Gambling",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200, (
        f"Expected 200 (form re-render) for invalid category, got {response.status_code}"
    )
    html = response.data.decode("utf-8")
    assert "error" in html.lower() or "valid category" in html.lower(), (
        "Expected an error message for an invalid category"
    )


def test_add_expense_invalid_category_does_not_insert(auth_client):
    """An invalid category must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "Gambling",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for invalid category, count changed {before} → {after}"
    )


def test_add_expense_empty_category_does_not_insert(auth_client):
    """Submitting an empty string for category must not create a new expense row."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "10.00",
        "category": "",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before, (
        f"Expected no new rows for empty category, count changed {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 16. Value preservation on validation failure
# ---------------------------------------------------------------------------

def test_add_expense_amount_error_preserves_category_in_form(auth_client):
    """On an amount validation error the submitted category must be echoed back."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Health",
        "date": "2026-06-20",
        "description": "Doctor visit",
    })
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    # The selected option for the preserved category is rendered with 'selected'
    assert "Health" in html, (
        "Expected the previously submitted category 'Health' to be echoed in the re-rendered form"
    )


def test_add_expense_amount_error_preserves_date_in_form(auth_client):
    """On an amount validation error the submitted date must be echoed back."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-05-15",
        "description": "",
    })
    assert response.status_code == 200
    assert b"2026-05-15" in response.data, (
        "Expected the previously submitted date '2026-05-15' to appear in the re-rendered form"
    )


def test_add_expense_amount_error_preserves_description_in_form(auth_client):
    """On an amount validation error the submitted description must be echoed back."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "-1",
        "category": "Other",
        "date": "2026-06-01",
        "description": "My special description",
    })
    assert response.status_code == 200
    assert b"My special description" in response.data, (
        "Expected the previously submitted description to appear in the re-rendered form"
    )


def test_add_expense_amount_error_preserves_amount_in_form(auth_client):
    """On an amount validation error the submitted (bad) amount must be echoed back."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "0",
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200
    # The template sets value="{{ amount or '' }}" — the literal "0" should appear.
    assert b"0" in response.data, (
        "Expected the previously submitted amount '0' to appear in the re-rendered form"
    )


def test_add_expense_category_error_preserves_amount(auth_client):
    """On a category validation error the submitted amount must be echoed back."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "42.00",
        "category": "InvalidCat",
        "date": "2026-06-20",
        "description": "",
    })
    assert response.status_code == 200
    assert b"42.00" in response.data, (
        "Expected the submitted amount '42.00' to be echoed in the re-rendered form"
    )


def test_add_expense_date_error_preserves_amount_and_category(auth_client):
    """On a date validation error the submitted amount and category must be echoed back."""
    client, user_id, db_path = auth_client
    response = client.post("/expenses/add", data={
        "amount": "55.00",
        "category": "Transport",
        "date": "bad-date",
        "description": "Train ticket",
    })
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "55.00" in html, (
        "Expected amount '55.00' to be preserved in form after date validation error"
    )
    assert "Transport" in html, (
        "Expected category 'Transport' to be preserved in form after date validation error"
    )


# ---------------------------------------------------------------------------
# 17. Valid POST without description → NULL in DB
# ---------------------------------------------------------------------------

def test_add_expense_no_description_inserts_null(auth_client):
    """Omitting description must succeed and store NULL (or empty) in the DB."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    client.post("/expenses/add", data={
        "amount": "7.50",
        "category": "Other",
        "date": "2026-06-19",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert after == before + 1, (
        "Expected one new expense row even when description is empty"
    )
    row = _fetch_latest_expense(db_path, user_id)
    assert row is not None
    # description should be None or an empty string — not a crash
    assert row["description"] is None or row["description"] == "", (
        f"Expected NULL or empty description, got {row['description']!r}"
    )


# ---------------------------------------------------------------------------
# 18. Parametrized invalid amounts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_amount", [
    "0",
    "0.00",
    "-1",
    "-0.01",
    "abc",
    "",
    "   ",
    "--5",
    "1e999",   # overflows to inf in some parsers; negative/zero after conversion
])
def test_add_expense_invalid_amounts_never_insert(auth_client, bad_amount):
    """Each invalid amount value must produce 200 + error and no DB insert."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    response = client.post("/expenses/add", data={
        "amount": bad_amount,
        "category": "Food",
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert response.status_code == 200, (
        f"Expected 200 for invalid amount {bad_amount!r}, got {response.status_code}"
    )
    assert after == before, (
        f"Expected no insert for invalid amount {bad_amount!r}, count {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 19. Parametrized valid categories — all 7 must succeed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("category", [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
])
def test_add_expense_all_valid_categories_succeed(auth_client, category):
    """Each of the 7 allowed categories must result in a successful insert + redirect."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": category,
        "date": "2026-06-20",
        "description": f"Test {category}",
    })
    after = _count_expenses(db_path, user_id)
    assert response.status_code == 302, (
        f"Expected 302 redirect for valid category '{category}', got {response.status_code}"
    )
    assert after == before + 1, (
        f"Expected one new row for category '{category}', count {before} → {after}"
    )


# ---------------------------------------------------------------------------
# 20. Parametrized invalid categories
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_category", [
    "Gambling",
    "food",          # case-sensitive check
    "FOOD",
    "travel",
    "medical",
    "",
    "   ",
    "<script>",      # injection attempt — must be safely rejected
    "Food; DROP TABLE expenses;--",  # SQL injection in form field
])
def test_add_expense_invalid_categories_never_insert(auth_client, bad_category):
    """Each invalid category must produce 200 + error and no DB insert."""
    client, user_id, db_path = auth_client
    before = _count_expenses(db_path, user_id)
    response = client.post("/expenses/add", data={
        "amount": "10.00",
        "category": bad_category,
        "date": "2026-06-20",
        "description": "",
    })
    after = _count_expenses(db_path, user_id)
    assert response.status_code == 200, (
        f"Expected 200 for invalid category {bad_category!r}, got {response.status_code}"
    )
    assert after == before, (
        f"Expected no insert for invalid category {bad_category!r}, count {before} → {after}"
    )
