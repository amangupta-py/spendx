"""
Unit tests for database query functions.

Covers:
  - get_user_by_id  (database.queries)
  - get_summary_stats (database.queries)
  - get_recent_transactions (database.queries)

Additional test modules can be appended or added alongside this file.
"""

import sqlite3
import pytest

import database.db as db_module
from database.db import init_db, seed_db, create_user
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Provide a fresh, seeded SQLite database for each test.

    - Points database.db.DB_PATH at a temp file so tests never touch
      the real spendly.db.
    - Calls init_db() to create the schema, then seed_db() to populate
      the demo user and 8 seed expenses.
    - Yields the Path to the temp db file (most tests can ignore this).
    """
    tmp_db = tmp_path / "test_spendly.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_db))
    init_db()
    seed_db()
    yield tmp_db


# ---------------------------------------------------------------------------
# Tests for get_user_by_id
# ---------------------------------------------------------------------------

class TestGetUserById:
    def test_existing_user_returns_correct_name(self, seeded_db):
        user = get_user_by_id(1)
        assert user is not None
        assert user["name"] == "Demo User"

    def test_existing_user_returns_correct_email(self, seeded_db):
        user = get_user_by_id(1)
        assert user is not None
        assert user["email"] == "demo@spendly.com"

    def test_existing_user_member_since_is_formatted(self, seeded_db):
        """member_since must be 'Month YYYY' (e.g. 'June 2026'), not a raw timestamp."""
        user = get_user_by_id(1)
        assert user is not None
        # Must match "Month YYYY" -- two space-separated tokens, second is 4 digits
        parts = user["member_since"].split()
        assert len(parts) == 2, f"Expected 'Month YYYY', got: {user['member_since']!r}"
        assert parts[1].isdigit() and len(parts[1]) == 4

    def test_nonexistent_user_returns_none(self, seeded_db):
        result = get_user_by_id(999)
        assert result is None


# ---------------------------------------------------------------------------
# Tests for get_summary_stats
# ---------------------------------------------------------------------------

class TestGetSummaryStats:
    def test_seed_user_total_spent(self, seeded_db):
        stats = get_summary_stats(1)
        # Seed expenses: 12.50+35.00+120.00+45.00+18.00+64.99+9.99+22.75 = 328.23
        assert stats["total_spent"] == "₹328.23"

    def test_seed_user_transaction_count(self, seeded_db):
        stats = get_summary_stats(1)
        assert stats["transaction_count"] == 8

    def test_seed_user_top_category(self, seeded_db):
        """Bills (Rs.120.00) is the single largest category in the seed data."""
        stats = get_summary_stats(1)
        assert stats["top_category"] == "Bills"

    def test_user_with_no_expenses_returns_zero_stats(self, seeded_db):
        """A freshly created user with no expenses should get safe zero-state values."""
        create_user("Empty User", "empty@spendly.com", "pass123")

        # Retrieve the new user's id from the db directly
        conn = sqlite3.connect(str(seeded_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("empty@spendly.com",)
        ).fetchone()
        conn.close()
        new_user_id = row["id"]

        stats = get_summary_stats(new_user_id)
        assert stats["total_spent"] == "₹0.00"
        assert stats["transaction_count"] == 0
        assert stats["top_category"] == "—"


# ---------------------------------------------------------------------------
# Tests for get_recent_transactions
# ---------------------------------------------------------------------------

class TestGetRecentTransactions:

    def test_returns_eight_items_for_seed_user(self, seeded_db):
        result = get_recent_transactions(user_id=1)
        assert len(result) == 8

    def test_first_item_is_newest(self, seeded_db):
        """Results must be ordered newest-first; seed data's latest date is 2026-06-20."""
        result = get_recent_transactions(user_id=1)
        assert result[0]["date"] == "20 Jun"

    def test_each_item_has_required_keys(self, seeded_db):
        result = get_recent_transactions(user_id=1)
        for item in result:
            assert "date" in item
            assert "description" in item
            assert "category" in item
            assert "amount" in item

    def test_all_amounts_start_with_rupee_sign(self, seeded_db):
        result = get_recent_transactions(user_id=1)
        for item in result:
            assert item["amount"].startswith("₹"), (
                f"Expected amount to start with ₹, got: {item['amount']!r}"
            )

    def test_returns_empty_list_for_user_with_no_expenses(self, seeded_db):
        create_user("No Expenses User", "noexp@spendly.com", "password123")

        conn = sqlite3.connect(str(seeded_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("noexp@spendly.com",)
        ).fetchone()
        conn.close()
        new_user_id = row["id"]

        result = get_recent_transactions(user_id=new_user_id)
        assert result == []


# ---------------------------------------------------------------------------
# Route test — newest-first ordering on GET /profile
# ---------------------------------------------------------------------------

@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """
    Flask test client backed by a fresh seeded temp DB, with user_id=1
    pre-loaded in the session so /profile renders without a redirect.
    """
    from app import app as flask_app

    tmp_db = tmp_path / "route_spendly.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_db))
    init_db()
    seed_db()

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"
        yield c


def test_profile_transactions_newest_before_oldest(app_client):
    """
    The rendered /profile page must contain '20 Jun' (newest seed date)
    before '01 Jun' (oldest seed date) in the HTML source, confirming
    that transactions are rendered in newest-first order.
    """
    response = app_client.get("/profile")

    assert response.status_code == 200
    html = response.data.decode("utf-8")

    pos_newest = html.find("20 Jun")
    pos_oldest = html.find("01 Jun")

    assert pos_newest != -1, "'20 Jun' not found in /profile response"
    assert pos_oldest != -1, "'01 Jun' not found in /profile response"
    assert pos_newest < pos_oldest, (
        "Expected '20 Jun' (newest) to appear before '01 Jun' (oldest) "
        "in the rendered HTML, but it did not."
    )


# ---------------------------------------------------------------------------
# Tests for get_category_breakdown
# ---------------------------------------------------------------------------

class TestGetCategoryBreakdown:

    def test_returns_seven_categories_for_seed_user(self, seeded_db):
        result = get_category_breakdown(1)
        assert len(result) == 7

    def test_first_category_is_bills(self, seeded_db):
        result = get_category_breakdown(1)
        assert result[0]["name"] == "Bills"

    def test_first_category_pct_is_100(self, seeded_db):
        result = get_category_breakdown(1)
        assert result[0]["pct"] == 100

    def test_all_pct_values_are_integers(self, seeded_db):
        result = get_category_breakdown(1)
        for item in result:
            assert isinstance(item["pct"], int)

    def test_all_amounts_start_with_rupee_sign(self, seeded_db):
        result = get_category_breakdown(1)
        for item in result:
            assert item["amount"].startswith("₹")

    def test_returns_empty_list_for_user_with_no_expenses(self, seeded_db):
        create_user("Cat Empty User", "catempty@spendly.com", "pass123")
        conn = sqlite3.connect(str(seeded_db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("catempty@spendly.com",)
        ).fetchone()
        conn.close()
        assert get_category_breakdown(row["id"]) == []


# ---------------------------------------------------------------------------
# Route tests — GET /profile
# ---------------------------------------------------------------------------

def test_profile_unauthenticated(tmp_path, monkeypatch):
    from app import app as flask_app
    tmp_db = tmp_path / "unauth_spendly.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_db))
    init_db()
    seed_db()
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as c:
        response = c.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_contains_real_data(app_client):
    response = app_client.get("/profile")
    assert response.status_code == 200
    data = response.data
    assert b"Demo User" in data
    assert b"demo@spendly.com" in data
    assert "₹".encode() in data
    assert b"Bills" in data
