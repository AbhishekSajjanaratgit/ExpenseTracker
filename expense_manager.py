"""
expense_manager.py
All business logic for the Expense Tracker: add/update/delete/list expenses,
summaries (overall + monthly), category filtering, budgets, and CSV export.

This module has no argparse/CLI code in it on purpose, so it can be tested
or reused independently of the command-line interface.
"""

import csv
from datetime import datetime

from db import get_connection

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ---------------------------------------------------------------------------
# Expenses: create / update / delete / read
# ---------------------------------------------------------------------------

def add_expense(description, amount, category="general", date=None):
    if not description or not description.strip():
        raise ValueError("Description cannot be empty.")
    if amount is None or amount <= 0:
        raise ValueError("Amount must be greater than 0.")

    date = date or datetime.now().strftime("%Y-%m-%d")
    category = (category or "general").strip().lower()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (date, description, amount, category) VALUES (?, ?, ?, ?)",
        (date, description.strip(), amount, category),
    )
    conn.commit()
    expense_id = cur.lastrowid
    conn.close()

    # Fire a budget warning immediately if this expense pushed the month over.
    dt = datetime.strptime(date, "%Y-%m-%d")
    check_budget_warning(dt.year, dt.month)

    return expense_id


def update_expense(expense_id, description=None, amount=None, category=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    row = cur.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Expense with id {expense_id} not found.")

    new_description = description.strip() if description is not None else row["description"]
    new_amount = amount if amount is not None else row["amount"]
    new_category = category.strip().lower() if category is not None else row["category"]

    if new_amount is None or new_amount <= 0:
        conn.close()
        raise ValueError("Amount must be greater than 0.")
    if not new_description:
        conn.close()
        raise ValueError("Description cannot be empty.")

    cur.execute(
        "UPDATE expenses SET description = ?, amount = ?, category = ? WHERE id = ?",
        (new_description, new_amount, new_category, expense_id),
    )
    conn.commit()
    conn.close()

    dt = datetime.strptime(row["date"], "%Y-%m-%d")
    check_budget_warning(dt.year, dt.month)


def delete_expense(expense_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
    if cur.fetchone() is None:
        conn.close()
        raise ValueError(f"Expense with id {expense_id} not found.")

    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def list_expenses(category=None):
    conn = get_connection()
    cur = conn.cursor()
    if category:
        cur.execute(
            "SELECT * FROM expenses WHERE category = ? ORDER BY date, id",
            (category.strip().lower(),),
        )
    else:
        cur.execute("SELECT * FROM expenses ORDER BY date, id")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

def summary_all(category=None):
    conn = get_connection()
    cur = conn.cursor()
    if category:
        cur.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE category = ?",
            (category.strip().lower(),),
        )
    else:
        cur.execute("SELECT SUM(amount) AS total FROM expenses")
    total = cur.fetchone()["total"] or 0.0
    conn.close()
    return total


def summary_by_month(month, year=None, category=None):
    year = year or datetime.now().year
    month_str = f"{year:04d}-{month:02d}"

    conn = get_connection()
    cur = conn.cursor()
    if category:
        cur.execute(
            "SELECT SUM(amount) AS total FROM expenses "
            "WHERE strftime('%Y-%m', date) = ? AND category = ?",
            (month_str, category.strip().lower()),
        )
    else:
        cur.execute(
            "SELECT SUM(amount) AS total FROM expenses WHERE strftime('%Y-%m', date) = ?",
            (month_str,),
        )
    total = cur.fetchone()["total"] or 0.0
    conn.close()
    return total


def category_breakdown(month=None, year=None):
    """Return list of (category, total) rows, optionally scoped to a month."""
    conn = get_connection()
    cur = conn.cursor()
    if month:
        year = year or datetime.now().year
        month_str = f"{year:04d}-{month:02d}"
        cur.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE strftime('%Y-%m', date) = ? GROUP BY category ORDER BY total DESC",
            (month_str,),
        )
    else:
        cur.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "GROUP BY category ORDER BY total DESC"
        )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------

def set_budget(year, month, amount):
    if not (1 <= month <= 12):
        raise ValueError("Month must be between 1 and 12.")
    if amount is None or amount <= 0:
        raise ValueError("Budget amount must be greater than 0.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO budgets (year, month, amount) VALUES (?, ?, ?)
        ON CONFLICT(year, month) DO UPDATE SET amount = excluded.amount
        """,
        (year, month, amount),
    )
    conn.commit()
    conn.close()


def get_budget(year, month):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT amount FROM budgets WHERE year = ? AND month = ?", (year, month))
    row = cur.fetchone()
    conn.close()
    return row["amount"] if row else None


def check_budget_warning(year, month):
    """Print a warning to stdout if spending for the given month exceeds its budget.
    Returns (spent, budget) or None if no budget is set for that month."""
    budget = get_budget(year, month)
    if budget is None:
        return None

    spent = summary_by_month(month, year)
    if spent > budget:
        print(
            f"⚠️  WARNING: You have exceeded your budget for "
            f"{MONTH_NAMES[month - 1]} {year}! "
            f"Spent: ${spent:.2f} / Budget: ${budget:.2f}"
        )
    return spent, budget


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_to_csv(output_path="expenses.csv"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, date, description, amount, category FROM expenses ORDER BY date, id")
    rows = cur.fetchall()
    conn.close()

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Date", "Description", "Amount", "Category"])
        for row in rows:
            writer.writerow(
                [row["id"], row["date"], row["description"], f"{row['amount']:.2f}", row["category"]]
            )
    return output_path
