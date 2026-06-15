import os
import sqlite3
import calendar
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "GET":
        return render_template("register.html")

    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.")

    flash("Account created! Please sign in.")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "GET":
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="All fields are required.")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session.clear()
    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


def resolve_date_filter(preset, raw_start, raw_end):
    today = date.today()
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    if preset == "this_month":
        return today.replace(day=1).isoformat(), today.isoformat(), "this_month"
    if preset == "last_3":
        d = today
        for _ in range(2):
            d = (d.replace(day=1) - timedelta(days=1))
        return d.replace(day=1).isoformat(), month_end.isoformat(), "last_3"
    if preset == "last_6":
        d = today
        for _ in range(5):
            d = (d.replace(day=1) - timedelta(days=1))
        return d.replace(day=1).isoformat(), month_end.isoformat(), "last_6"
    if raw_start and raw_end:
        try:
            datetime.strptime(raw_start, "%Y-%m-%d")
            datetime.strptime(raw_end, "%Y-%m-%d")
            return raw_start, raw_end, "custom"
        except ValueError:
            pass
    return None, None, "all"


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    start_date, end_date, active_preset = resolve_date_filter(
        request.args.get("preset", ""),
        request.args.get("start_date", "").strip(),
        request.args.get("end_date", "").strip(),
    )

    stats        = get_summary_stats(session["user_id"], start_date=start_date, end_date=end_date)
    transactions = get_recent_transactions(session["user_id"], start_date=start_date, end_date=end_date)
    categories   = get_category_breakdown(session["user_id"], start_date=start_date, end_date=end_date)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        active_preset=active_preset,
        start_date=start_date or "",
        end_date=end_date or "",
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
