from datetime import datetime
from database.db import get_db


def _date_filter(start_date, end_date):
    if start_date and end_date:
        return " AND date BETWEEN ? AND ?", (start_date, end_date)
    return "", ()


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    dt = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": dt.strftime("%B %Y"),
    }


def get_summary_stats(user_id, start_date=None, end_date=None):
    date_clause, date_params = _date_filter(start_date, end_date)
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?" + date_clause,
        (user_id,) + date_params,
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses WHERE user_id = ?" + date_clause +
        " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        (user_id,) + date_params,
    ).fetchone()
    conn.close()
    return {
        "total_spent": f"₹{row['total']:.2f}",
        "transaction_count": row["cnt"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    date_clause, date_params = _date_filter(start_date, end_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount FROM expenses WHERE user_id = ?" + date_clause +
        " ORDER BY date DESC LIMIT ?",
        (user_id,) + date_params + (limit,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        dt = datetime.strptime(r["date"], "%Y-%m-%d")
        result.append({
            "date": dt.strftime("%d %b"),
            "description": r["description"],
            "category": r["category"],
            "amount": f"₹{r['amount']:.2f}",
        })
    return result


def get_category_breakdown(user_id, start_date=None, end_date=None):
    date_clause, date_params = _date_filter(start_date, end_date)
    conn = get_db()
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS total FROM expenses WHERE user_id = ?" + date_clause +
        " GROUP BY category ORDER BY total DESC",
        (user_id,) + date_params,
    ).fetchall()
    conn.close()
    if not rows:
        return []
    max_total = rows[0]["total"]
    return [
        {
            "name": r["name"],
            "amount": f"₹{r['total']:.2f}",
            "pct": round(r["total"] / max_total * 100),
        }
        for r in rows
    ]
