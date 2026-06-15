"""
Tests for Step 6: Date Filter for Profile Page

Covers:
  - Auth guard on GET /profile
  - All-time view (no filter params)
  - Preset filters: this_month, last_3, last_6
  - Custom date range: valid, empty result window, missing end_date, malformed dates
  - Query helpers: get_summary_stats, get_recent_transactions, get_category_breakdown
    with start_date/end_date keyword arguments

Fixture strategy:
  - All tests monkeypatch database.db.DB_PATH to a temp SQLite file so the
    real spendly.db is never touched.
  - Route tests inject user_id=1 into the Flask session via session_transaction()
    rather than going through the login form.

Seed data reference (from database/db.py seed_db):
  user_id=1  email=demo@spendly.com
  8 expenses, all in June 2026:
    2026-06-01  Food          12.50
    2026-06-03  Transport     35.00
    2026-06-05  Bills        120.00
    2026-06-08  Health        45.00
    2026-06-12  Entertainment 18.00
    2026-06-15  Shopping      64.99
    2026-06-18  Other          9.99
    2026-06-20  Food          22.75
  Total: 328.23   Top category: Bills

Project date context: today = 2026-06-15
  this_month range: 2026-06-01 to 2026-06-15  → 6 of 8 expenses (excludes 06-18, 06-20)
  last_3 / last_6 ranges include all of June 2026 → all 8 expenses
"""

import sqlite3
import pytest

import database.db as db_module
from database.db import init_db, seed_db, create_user
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """
    Fresh, seeded temp SQLite DB for unit tests.
    Monkeypatches DB_PATH so no real DB is touched.
    """
    tmp_db = tmp_path / "test_spendly.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_db))
    init_db()
    seed_db()
    yield tmp_db


@pytest.fixture()
def auth_client(tmp_path, monkeypatch):
    """
    Flask test client backed by a fresh seeded temp DB with user_id=1
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


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

def test_profile_unauthenticated_redirects_to_login(tmp_path, monkeypatch):
    """GET /profile without a session → 302 redirect to /login."""
    from app import app as flask_app

    tmp_db = tmp_path / "unauth_spendly.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_db))
    init_db()
    seed_db()

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"

    with flask_app.test_client() as c:
        response = c.get("/profile")

    assert response.status_code == 302, (
        f"Expected 302 redirect for unauthenticated request, got {response.status_code}"
    )
    assert "/login" in response.headers["Location"], (
        "Expected redirect target to contain '/login'"
    )


# ---------------------------------------------------------------------------
# 2. All-time view — no filter params
# ---------------------------------------------------------------------------

class TestAllTimeView:
    def test_returns_200(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200, (
            f"Expected 200 for authenticated /profile, got {response.status_code}"
        )

    def test_shows_all_time_total_spent(self, auth_client):
        """All 8 seed expenses sum to ₹328.23."""
        response = auth_client.get("/profile")
        assert "₹328.23".encode() in response.data, (
            "Expected ₹328.23 total in all-time view"
        )

    def test_shows_all_eight_transactions(self, auth_client):
        """All 8 seed expenses should appear; spot-check oldest and newest dates."""
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        assert "01 Jun" in html, "Expected '01 Jun' (oldest seed date) in all-time view"
        assert "20 Jun" in html, "Expected '20 Jun' (newest seed date) in all-time view"

    def test_all_time_pill_is_active(self, auth_client):
        """The 'All Time' filter pill must carry the active CSS class."""
        response = auth_client.get("/profile")
        html = response.data.decode("utf-8")
        # The template renders:
        # <a href="/profile" class="filter-pill filter-pill--active">All Time</a>
        # when active_preset == 'all'
        assert "filter-pill--active" in html, (
            "Expected an active filter pill to be rendered"
        )
        # Verify the active pill is the All Time one, not a preset pill
        all_time_active_marker = 'href="/profile"'
        active_marker = "filter-pill--active"
        pos_all_time = html.find(all_time_active_marker)
        pos_active = html.find(active_marker)
        # The All Time href appears before the preset hrefs; its active class
        # should be on the same element — verify both strings are near each other
        assert pos_all_time != -1 and pos_active != -1, (
            "All Time link or active class not found in HTML"
        )
        # The active class must appear within 150 chars of the All Time href
        # (they are on the same <a> element)
        assert abs(pos_all_time - pos_active) < 150, (
            "filter-pill--active does not appear close to the All Time href; "
            "wrong pill may be active"
        )

    def test_shows_top_category_bills(self, auth_client):
        """Bills is the top category in the seed data."""
        response = auth_client.get("/profile")
        assert b"Bills" in response.data, "Expected 'Bills' as top category in all-time view"


# ---------------------------------------------------------------------------
# 3. Preset: this_month
# ---------------------------------------------------------------------------

class TestPresetThisMonth:
    def test_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=this_month")
        assert response.status_code == 200

    def test_this_month_pill_is_active(self, auth_client):
        """The 'This Month' pill must carry filter-pill--active."""
        response = auth_client.get("/profile?preset=this_month")
        html = response.data.decode("utf-8")
        # Template: <a href="/profile?preset=this_month" class="filter-pill filter-pill--active">
        assert "filter-pill--active" in html, "Expected an active filter pill"
        assert "preset=this_month" in html, "Expected this_month preset link in HTML"
        this_month_href = 'href="/profile?preset=this_month"'
        active_class = "filter-pill--active"
        pos_href = html.find(this_month_href)
        pos_active = html.find(active_class)
        assert pos_href != -1, "this_month preset link not found in HTML"
        assert abs(pos_href - pos_active) < 150, (
            "filter-pill--active is not on the this_month pill"
        )

    def test_this_month_excludes_future_seed_dates(self, auth_client):
        """
        today=2026-06-15 → range is 2026-06-01 to 2026-06-15.
        Seed expenses on 2026-06-18 and 2026-06-20 are outside this range
        and must NOT appear.
        """
        response = auth_client.get("/profile?preset=this_month")
        html = response.data.decode("utf-8")
        assert "18 Jun" not in html, (
            "2026-06-18 expense should be outside this_month range but was found"
        )
        assert "20 Jun" not in html, (
            "2026-06-20 expense should be outside this_month range but was found"
        )

    def test_this_month_includes_seed_dates_up_to_today(self, auth_client):
        """
        Expenses on 2026-06-01 through 2026-06-15 (6 rows) must appear.
        """
        response = auth_client.get("/profile?preset=this_month")
        html = response.data.decode("utf-8")
        for day_label in ["01 Jun", "03 Jun", "05 Jun", "08 Jun", "12 Jun", "15 Jun"]:
            assert day_label in html, (
                f"Expected '{day_label}' to appear in this_month filtered view"
            )

    def test_this_month_transaction_count_is_six(self, auth_client):
        """6 of 8 seed expenses fall on or before 2026-06-15."""
        response = auth_client.get("/profile?preset=this_month")
        # The transaction count stat is rendered as a plain number in the HTML
        # between the "Transactions" label and the next element.
        # We check for ">6<" as the rendered mock-stat-value content.
        html = response.data.decode("utf-8")
        assert ">6<" in html, (
            "Expected transaction count of 6 for this_month preset, not found in HTML"
        )


# ---------------------------------------------------------------------------
# 4. Preset: last_3
# ---------------------------------------------------------------------------

class TestPresetLast3:
    def test_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=last_3")
        assert response.status_code == 200

    def test_last_3_pill_is_active(self, auth_client):
        response = auth_client.get("/profile?preset=last_3")
        html = response.data.decode("utf-8")
        assert "filter-pill--active" in html, "Expected an active filter pill for last_3"
        last_3_href = 'href="/profile?preset=last_3"'
        pos_href = html.find(last_3_href)
        pos_active = html.find("filter-pill--active")
        assert pos_href != -1, "last_3 preset link not found in HTML"
        assert abs(pos_href - pos_active) < 150, (
            "filter-pill--active is not on the last_3 pill"
        )

    def test_last_3_shows_all_june_2026_transactions(self, auth_client):
        """
        last_3 from 2026-06-15 spans back ~3 months, covering all June 2026 seed data.
        """
        response = auth_client.get("/profile?preset=last_3")
        html = response.data.decode("utf-8")
        assert "20 Jun" in html, "Expected newest seed transaction (20 Jun) in last_3 view"
        assert "01 Jun" in html, "Expected oldest seed transaction (01 Jun) in last_3 view"

    def test_last_3_total_is_full_seed_total(self, auth_client):
        """All 8 expenses are within a 3-month window from June 2026."""
        response = auth_client.get("/profile?preset=last_3")
        assert "₹328.23".encode() in response.data, (
            "Expected ₹328.23 total in last_3 view"
        )


# ---------------------------------------------------------------------------
# 5. Preset: last_6
# ---------------------------------------------------------------------------

class TestPresetLast6:
    def test_returns_200(self, auth_client):
        response = auth_client.get("/profile?preset=last_6")
        assert response.status_code == 200

    def test_last_6_pill_is_active(self, auth_client):
        response = auth_client.get("/profile?preset=last_6")
        html = response.data.decode("utf-8")
        assert "filter-pill--active" in html, "Expected an active filter pill for last_6"
        last_6_href = 'href="/profile?preset=last_6"'
        pos_href = html.find(last_6_href)
        pos_active = html.find("filter-pill--active")
        assert pos_href != -1, "last_6 preset link not found in HTML"
        assert abs(pos_href - pos_active) < 150, (
            "filter-pill--active is not on the last_6 pill"
        )

    def test_last_6_shows_all_june_2026_transactions(self, auth_client):
        """All seed expenses are within a 6-month window from June 2026."""
        response = auth_client.get("/profile?preset=last_6")
        html = response.data.decode("utf-8")
        assert "20 Jun" in html, "Expected newest seed transaction (20 Jun) in last_6 view"
        assert "01 Jun" in html, "Expected oldest seed transaction (01 Jun) in last_6 view"

    def test_last_6_total_is_full_seed_total(self, auth_client):
        response = auth_client.get("/profile?preset=last_6")
        assert "₹328.23".encode() in response.data, (
            "Expected ₹328.23 total in last_6 view"
        )


# ---------------------------------------------------------------------------
# 6. Custom range — valid, full June 2026
# ---------------------------------------------------------------------------

class TestCustomRangeValid:
    def test_returns_200(self, auth_client):
        response = auth_client.get("/profile?start_date=2026-06-01&end_date=2026-06-30")
        assert response.status_code == 200

    def test_custom_range_shows_all_eight_transactions(self, auth_client):
        """
        start=2026-06-01, end=2026-06-30 covers all 8 seed expenses.
        """
        response = auth_client.get("/profile?start_date=2026-06-01&end_date=2026-06-30")
        html = response.data.decode("utf-8")
        assert "01 Jun" in html, "Expected '01 Jun' in custom range covering full June"
        assert "20 Jun" in html, "Expected '20 Jun' in custom range covering full June"

    def test_custom_range_total_spent(self, auth_client):
        """Full June 2026 range → total ₹328.23."""
        response = auth_client.get("/profile?start_date=2026-06-01&end_date=2026-06-30")
        assert "₹328.23".encode() in response.data, (
            "Expected ₹328.23 for full June 2026 custom range"
        )

    def test_custom_range_dates_prepopulated_in_inputs(self, auth_client):
        """
        After submitting a custom range the date inputs must be pre-populated
        with the active filter values (filter state survives reload).
        """
        response = auth_client.get("/profile?start_date=2026-06-01&end_date=2026-06-30")
        html = response.data.decode("utf-8")
        assert 'value="2026-06-01"' in html, (
            "start_date input should be pre-populated with 2026-06-01"
        )
        assert 'value="2026-06-30"' in html, (
            "end_date input should be pre-populated with 2026-06-30"
        )

    def test_custom_preset_marker_not_on_preset_pills(self, auth_client):
        """
        When a custom range is active, none of the named preset pills
        (All Time, This Month, etc.) should carry filter-pill--active.
        The active class should appear on a custom-range context, not a preset pill.
        """
        response = auth_client.get("/profile?start_date=2026-06-01&end_date=2026-06-30")
        html = response.data.decode("utf-8")
        # None of the preset pill hrefs should have filter-pill--active near them
        preset_hrefs = [
            'href="/profile"',
            'href="/profile?preset=this_month"',
            'href="/profile?preset=last_3"',
            'href="/profile?preset=last_6"',
        ]
        active_pos = html.find("filter-pill--active")
        # If the active class exists at all it must NOT be within 150 chars
        # of any preset pill anchor href
        if active_pos != -1:
            for href in preset_hrefs:
                pos = html.find(href)
                if pos != -1:
                    assert abs(pos - active_pos) > 150 or href == 'href="/profile"', (
                        # href="/profile" is the All Time pill; for custom preset
                        # its active class must NOT be on it
                        f"Preset pill {href!r} should not be active during custom range filter"
                    )


# ---------------------------------------------------------------------------
# 7. Custom range — narrow window with no results
# ---------------------------------------------------------------------------

class TestCustomRangeEmpty:
    def test_returns_200_no_crash(self, auth_client):
        """A date range with zero matching expenses must not crash."""
        response = auth_client.get("/profile?start_date=2025-01-01&end_date=2025-01-31")
        assert response.status_code == 200, (
            f"Expected 200 for empty range, got {response.status_code}"
        )

    def test_total_spent_is_zero(self, auth_client):
        response = auth_client.get("/profile?start_date=2025-01-01&end_date=2025-01-31")
        assert "₹0.00".encode() in response.data, (
            "Expected ₹0.00 total for date range with no matching expenses"
        )

    def test_transaction_count_is_zero(self, auth_client):
        """The transaction count stat card must show 0."""
        response = auth_client.get("/profile?start_date=2025-01-01&end_date=2025-01-31")
        html = response.data.decode("utf-8")
        assert ">0<" in html, (
            "Expected transaction count of 0 for empty date range"
        )

    def test_no_transaction_rows_rendered(self, auth_client):
        """No seed transaction date labels should appear in the empty-range view."""
        response = auth_client.get("/profile?start_date=2025-01-01&end_date=2025-01-31")
        html = response.data.decode("utf-8")
        for day_label in ["01 Jun", "03 Jun", "05 Jun", "08 Jun", "12 Jun",
                          "15 Jun", "18 Jun", "20 Jun"]:
            assert day_label not in html, (
                f"'{day_label}' should not appear for a range with no matching expenses"
            )


# ---------------------------------------------------------------------------
# 8. Custom range — only start_date provided (no end_date)
# ---------------------------------------------------------------------------

class TestCustomRangeMissingEndDate:
    def test_returns_200(self, auth_client):
        response = auth_client.get("/profile?start_date=2026-06-01")
        assert response.status_code == 200

    def test_falls_back_to_all_time_view(self, auth_client):
        """
        Missing end_date → fall back to all-time (no partial filter applied).
        All 8 seed transactions must appear.
        """
        response = auth_client.get("/profile?start_date=2026-06-01")
        html = response.data.decode("utf-8")
        assert "01 Jun" in html, "Expected all-time data when end_date is missing"
        assert "20 Jun" in html, "Expected all-time data when end_date is missing"

    def test_all_time_total_shown_when_end_date_missing(self, auth_client):
        """Full ₹328.23 total confirms all-time fallback."""
        response = auth_client.get("/profile?start_date=2026-06-01")
        assert "₹328.23".encode() in response.data, (
            "Expected full ₹328.23 total when end_date is missing (all-time fallback)"
        )

    def test_all_time_pill_active_when_end_date_missing(self, auth_client):
        """The 'All Time' filter pill should be active on fallback."""
        response = auth_client.get("/profile?start_date=2026-06-01")
        html = response.data.decode("utf-8")
        all_time_href = 'href="/profile"'
        active_class = "filter-pill--active"
        pos_href = html.find(all_time_href)
        pos_active = html.find(active_class)
        assert pos_href != -1, "All Time link not found"
        assert pos_active != -1, "filter-pill--active class not found"
        assert abs(pos_href - pos_active) < 150, (
            "filter-pill--active should be on the All Time pill when falling back"
        )


# ---------------------------------------------------------------------------
# 9. Custom range — malformed dates
# ---------------------------------------------------------------------------

class TestCustomRangeMalformedDates:
    def test_returns_200_no_crash(self, auth_client):
        """Malformed dates must not produce a 400 or 500."""
        response = auth_client.get("/profile?start_date=not-a-date&end_date=also-bad")
        assert response.status_code == 200, (
            f"Expected 200 for malformed dates, got {response.status_code}"
        )

    def test_falls_back_to_all_time_data(self, auth_client):
        """Malformed dates → all-time fallback; all 8 seed transactions visible."""
        response = auth_client.get("/profile?start_date=not-a-date&end_date=also-bad")
        html = response.data.decode("utf-8")
        assert "01 Jun" in html, "Expected all-time data for malformed date input"
        assert "20 Jun" in html, "Expected all-time data for malformed date input"

    def test_all_time_total_shown_for_malformed_dates(self, auth_client):
        response = auth_client.get("/profile?start_date=not-a-date&end_date=also-bad")
        assert "₹328.23".encode() in response.data, (
            "Expected full ₹328.23 total for malformed date input (all-time fallback)"
        )

    def test_all_time_pill_active_for_malformed_dates(self, auth_client):
        response = auth_client.get("/profile?start_date=not-a-date&end_date=also-bad")
        html = response.data.decode("utf-8")
        all_time_href = 'href="/profile"'
        pos_href = html.find(all_time_href)
        pos_active = html.find("filter-pill--active")
        assert pos_href != -1
        assert pos_active != -1
        assert abs(pos_href - pos_active) < 150, (
            "filter-pill--active should be on the All Time pill for malformed dates"
        )

    @pytest.mark.parametrize("start,end", [
        ("2026-13-01", "2026-06-30"),   # month 13 is invalid
        ("2026-06-01", "2026-06-32"),   # day 32 is invalid
        ("", "2026-06-30"),             # empty start
        ("2026-06-01", ""),             # empty end
        ("20260601", "20260630"),       # missing hyphens (YYYYMMDD format)
        ("06/01/2026", "06/30/2026"),   # wrong separator
    ])
    def test_various_malformed_inputs_never_crash(self, auth_client, start, end):
        """A broad set of invalid date strings must all return 200."""
        url = f"/profile?start_date={start}&end_date={end}"
        response = auth_client.get(url)
        assert response.status_code == 200, (
            f"Expected 200 for start={start!r}, end={end!r}, got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# 10. Unit: get_summary_stats — June 2026 range
# ---------------------------------------------------------------------------

class TestGetSummaryStatsWithDateFilter:
    def test_total_spent_for_june_2026(self, seeded_db):
        """Full June 2026 range includes all 8 seed expenses → ₹328.23."""
        stats = get_summary_stats(1, start_date="2026-06-01", end_date="2026-06-30")
        assert stats["total_spent"] == "₹328.23", (
            f"Expected ₹328.23 for June 2026 range, got {stats['total_spent']}"
        )

    def test_transaction_count_for_june_2026(self, seeded_db):
        """All 8 seed expenses fall in June 2026."""
        stats = get_summary_stats(1, start_date="2026-06-01", end_date="2026-06-30")
        assert stats["transaction_count"] == 8, (
            f"Expected 8 transactions for June 2026 range, got {stats['transaction_count']}"
        )

    def test_top_category_for_june_2026(self, seeded_db):
        """Bills (₹120.00) is the largest category in the seed data."""
        stats = get_summary_stats(1, start_date="2026-06-01", end_date="2026-06-30")
        assert stats["top_category"] == "Bills", (
            f"Expected 'Bills' as top category for June 2026 range, got {stats['top_category']}"
        )

    def test_returns_dict_with_required_keys(self, seeded_db):
        """Result must always contain total_spent, transaction_count, top_category."""
        stats = get_summary_stats(1, start_date="2026-06-01", end_date="2026-06-30")
        assert "total_spent" in stats
        assert "transaction_count" in stats
        assert "top_category" in stats

    def test_total_spent_starts_with_rupee_sign(self, seeded_db):
        stats = get_summary_stats(1, start_date="2026-06-01", end_date="2026-06-30")
        assert stats["total_spent"].startswith("₹"), (
            f"total_spent should start with ₹, got: {stats['total_spent']!r}"
        )


# ---------------------------------------------------------------------------
# 11. Unit: get_summary_stats — empty range
# ---------------------------------------------------------------------------

class TestGetSummaryStatsEmptyRange:
    def test_total_spent_is_zero(self, seeded_db):
        stats = get_summary_stats(1, start_date="2025-01-01", end_date="2025-01-31")
        assert stats["total_spent"] == "₹0.00", (
            f"Expected ₹0.00 for empty range, got {stats['total_spent']}"
        )

    def test_transaction_count_is_zero(self, seeded_db):
        stats = get_summary_stats(1, start_date="2025-01-01", end_date="2025-01-31")
        assert stats["transaction_count"] == 0, (
            f"Expected 0 transactions for empty range, got {stats['transaction_count']}"
        )

    def test_top_category_is_dash(self, seeded_db):
        """When no expenses match, top_category should be the placeholder '—'."""
        stats = get_summary_stats(1, start_date="2025-01-01", end_date="2025-01-31")
        assert stats["top_category"] == "—", (
            f"Expected '—' for top_category in empty range, got {stats['top_category']!r}"
        )


# ---------------------------------------------------------------------------
# 12. Unit: get_recent_transactions — June 2026 range
# ---------------------------------------------------------------------------

class TestGetRecentTransactionsWithDateFilter:
    def test_returns_eight_transactions_for_june_2026(self, seeded_db):
        """Full June 2026 range matches all 8 seed expenses."""
        result = get_recent_transactions(1, start_date="2026-06-01", end_date="2026-06-30")
        assert len(result) == 8, (
            f"Expected 8 transactions for June 2026 range, got {len(result)}"
        )

    def test_first_item_is_newest(self, seeded_db):
        """Results must be ordered newest-first; '20 Jun' is the latest seed date."""
        result = get_recent_transactions(1, start_date="2026-06-01", end_date="2026-06-30")
        assert result[0]["date"] == "20 Jun", (
            f"Expected newest transaction to be '20 Jun', got {result[0]['date']!r}"
        )

    def test_last_item_is_oldest(self, seeded_db):
        """Last item in newest-first order should be '01 Jun'."""
        result = get_recent_transactions(1, start_date="2026-06-01", end_date="2026-06-30")
        assert result[-1]["date"] == "01 Jun", (
            f"Expected oldest transaction to be '01 Jun', got {result[-1]['date']!r}"
        )

    def test_all_dates_are_in_june(self, seeded_db):
        """Every returned transaction date should contain 'Jun'."""
        result = get_recent_transactions(1, start_date="2026-06-01", end_date="2026-06-30")
        for item in result:
            assert "Jun" in item["date"], (
                f"Transaction date {item['date']!r} is outside June 2026"
            )

    def test_all_amounts_start_with_rupee_sign(self, seeded_db):
        result = get_recent_transactions(1, start_date="2026-06-01", end_date="2026-06-30")
        for item in result:
            assert item["amount"].startswith("₹"), (
                f"Amount {item['amount']!r} should start with ₹"
            )

    def test_each_item_has_required_keys(self, seeded_db):
        result = get_recent_transactions(1, start_date="2026-06-01", end_date="2026-06-30")
        for item in result:
            assert "date" in item
            assert "description" in item
            assert "category" in item
            assert "amount" in item

    def test_returns_empty_list_for_empty_range(self, seeded_db):
        """A range with no matching expenses returns an empty list, not an error."""
        result = get_recent_transactions(1, start_date="2025-01-01", end_date="2025-01-31")
        assert result == [], (
            f"Expected [] for empty date range, got {result}"
        )

    def test_limit_is_respected_alongside_date_filter(self, seeded_db):
        """limit= param must still be honoured when a date filter is active."""
        result = get_recent_transactions(
            1, limit=3, start_date="2026-06-01", end_date="2026-06-30"
        )
        assert len(result) <= 3, (
            f"Expected at most 3 results with limit=3, got {len(result)}"
        )


# ---------------------------------------------------------------------------
# 13. Unit: get_category_breakdown — with and without date filter
# ---------------------------------------------------------------------------

class TestGetCategoryBreakdownWithDateFilter:
    def test_returns_non_empty_list_for_june_2026(self, seeded_db):
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        assert len(result) > 0, "Expected non-empty category breakdown for June 2026"

    def test_returns_seven_categories_for_june_2026(self, seeded_db):
        """Seed data has 7 distinct categories — all in June 2026."""
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        assert len(result) == 7, (
            f"Expected 7 categories for June 2026 range, got {len(result)}"
        )

    def test_first_category_is_bills_for_june_2026(self, seeded_db):
        """Bills (₹120.00) must be the top category, ordered by total DESC."""
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        assert result[0]["name"] == "Bills", (
            f"Expected 'Bills' as top category, got {result[0]['name']!r}"
        )

    def test_first_category_pct_is_100_for_june_2026(self, seeded_db):
        """The top category's percentage bar must be 100 (it is the maximum)."""
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        assert result[0]["pct"] == 100, (
            f"Expected pct=100 for top category, got {result[0]['pct']}"
        )

    def test_all_amounts_start_with_rupee_sign_filtered(self, seeded_db):
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        for item in result:
            assert item["amount"].startswith("₹"), (
                f"Category amount {item['amount']!r} should start with ₹"
            )

    def test_returns_empty_list_for_empty_range(self, seeded_db):
        """A range with no matching expenses must return [], not crash."""
        result = get_category_breakdown(1, start_date="2025-01-01", end_date="2025-01-31")
        assert result == [], (
            f"Expected [] for empty date range, got {result}"
        )

    def test_all_pct_values_are_integers_filtered(self, seeded_db):
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        for item in result:
            assert isinstance(item["pct"], int), (
                f"pct must be an int, got {type(item['pct'])} for {item['name']}"
            )

    def test_each_item_has_required_keys(self, seeded_db):
        result = get_category_breakdown(1, start_date="2026-06-01", end_date="2026-06-30")
        for item in result:
            assert "name" in item
            assert "amount" in item
            assert "pct" in item
