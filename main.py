#!/usr/bin/env python3
"""
main.py
Command-line entry point for the Expense Tracker application.

Run `python main.py -h` (or `python main.py <command> -h`) for usage help.
"""

import argparse
import sys
from datetime import datetime

from db import init_db
import expense_manager as em

MONTH_NAMES = em.MONTH_NAMES


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def print_expenses_table(rows):
    if not rows:
        print("No expenses found.")
        return

    headers = ["ID", "Date", "Description", "Amount", "Category"]
    widths = [5, 12, 32, 12, 15]

    print("".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("-" * sum(widths))
    for row in rows:
        desc = row["description"]
        if len(desc) > 30:
            desc = desc[:27] + "..."
        print(
            str(row["id"]).ljust(widths[0])
            + str(row["date"]).ljust(widths[1])
            + desc.ljust(widths[2])
            + f"${row['amount']:.2f}".ljust(widths[3])
            + str(row["category"]).ljust(widths[4])
        )


def print_category_breakdown(rows):
    if not rows:
        return
    print("\nBy category:")
    for row in rows:
        print(f"  {row['category']:<15} ${row['total']:.2f}")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_add(args):
    try:
        expense_id = em.add_expense(args.description, args.amount, args.category)
        print(f"Expense added successfully (ID: {expense_id})")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_update(args):
    if args.description is None and args.amount is None and args.category is None:
        print("Error: provide at least one of --description, --amount, --category to update.")
        sys.exit(1)
    try:
        em.update_expense(args.id, args.description, args.amount, args.category)
        print(f"Expense updated successfully (ID: {args.id})")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_delete(args):
    try:
        em.delete_expense(args.id)
        print(f"Expense deleted successfully (ID: {args.id})")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_list(args):
    rows = em.list_expenses(category=args.category)
    print_expenses_table(rows)


def cmd_summary(args):
    if args.month is not None:
        if not (1 <= args.month <= 12):
            print("Error: --month must be between 1 and 12.")
            sys.exit(1)

        year = args.year or datetime.now().year
        total = em.summary_by_month(args.month, year, category=args.category)
        label = f"{MONTH_NAMES[args.month - 1]} {year}"
        print(f"Total expenses for {label}: ${total:.2f}")

        if not args.category:
            budget = em.get_budget(year, args.month)
            if budget is not None:
                remaining = budget - total
                print(f"Budget: ${budget:.2f} | Remaining: ${remaining:.2f}")
                if total > budget:
                    print(f"⚠️  WARNING: You have exceeded your budget for {label}!")

        print_category_breakdown(em.category_breakdown(month=args.month, year=year))
    else:
        total = em.summary_all(category=args.category)
        print(f"Total expenses: ${total:.2f}")
        if not args.category:
            print_category_breakdown(em.category_breakdown())


def cmd_budget(args):
    try:
        year = args.year or datetime.now().year
        em.set_budget(year, args.month, args.amount)
        print(f"Budget for {MONTH_NAMES[args.month - 1]} {year} set to ${args.amount:.2f}")
        em.check_budget_warning(year, args.month)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_export(args):
    path = em.export_to_csv(args.output)
    print(f"Expenses exported to {path}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="A simple command-line expense tracker backed by SQLite.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = subparsers.add_parser("add", help="Add a new expense")
    p_add.add_argument("--description", required=True, help="Expense description")
    p_add.add_argument("--amount", required=True, type=float, help="Expense amount")
    p_add.add_argument("--category", default="general", help="Expense category (default: general)")
    p_add.set_defaults(func=cmd_add)

    # update
    p_update = subparsers.add_parser("update", help="Update an existing expense")
    p_update.add_argument("--id", required=True, type=int, help="Expense ID to update")
    p_update.add_argument("--description", default=None, help="New description")
    p_update.add_argument("--amount", default=None, type=float, help="New amount")
    p_update.add_argument("--category", default=None, help="New category")
    p_update.set_defaults(func=cmd_update)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete an expense")
    p_delete.add_argument("--id", required=True, type=int, help="Expense ID to delete")
    p_delete.set_defaults(func=cmd_delete)

    # list
    p_list = subparsers.add_parser("list", help="View all expenses")
    p_list.add_argument("--category", default=None, help="Filter by category")
    p_list.set_defaults(func=cmd_list)

    # summary
    p_summary = subparsers.add_parser("summary", help="View a summary of expenses")
    p_summary.add_argument("--month", type=int, default=None, help="Month number 1-12 (current year unless --year given)")
    p_summary.add_argument("--year", type=int, default=None, help="Year (default: current year, used with --month)")
    p_summary.add_argument("--category", default=None, help="Filter by category")
    p_summary.set_defaults(func=cmd_summary)

    # budget
    p_budget = subparsers.add_parser("budget", help="Set a monthly budget")
    p_budget.add_argument("--month", required=True, type=int, help="Month number 1-12")
    p_budget.add_argument("--year", type=int, default=None, help="Year (default: current year)")
    p_budget.add_argument("--amount", required=True, type=float, help="Budget amount")
    p_budget.set_defaults(func=cmd_budget)

    # export
    p_export = subparsers.add_parser("export", help="Export all expenses to a CSV file")
    p_export.add_argument("--output", default="expenses.csv", help="Output CSV file path (default: expenses.csv)")
    p_export.set_defaults(func=cmd_export)

    return parser


def main():
    init_db()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
