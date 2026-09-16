# Expense Tracker (CLI)

A command-line expense tracker built with **Python's `argparse`** and **SQLite**.
No third-party dependencies required — pure standard library.

## Project structure

```
expense_tracker/
├── main.py              # CLI entry point (argparse subcommands)
├── expense_manager.py   # Business logic: CRUD, summaries, budgets, CSV export
├── db.py                # SQLite connection + schema setup
├── requirements.txt     # (empty on purpose — stdlib only)
├── README.md
└── expenses.db          # created automatically on first run
```

## Requirements

- Python 3.8+
- No external packages needed.

## Running

From inside the `expense_tracker/` directory:

```bash
python main.py <command> [options]
```

The SQLite database file `expenses.db` is created automatically next to
`main.py` the first time you run any command.

## Commands

### Add an expense
```bash
python main.py add --description "Lunch" --amount 20 --category food
# Expense added successfully (ID: 1)
```
`--category` is optional and defaults to `general`.

### Update an expense
```bash
python main.py update --id 1 --amount 25
python main.py update --id 1 --description "Lunch with client" --category food
```
Provide only the fields you want to change; the rest stay the same.

### Delete an expense
```bash
python main.py delete --id 1
```

### View all expenses
```bash
python main.py list
python main.py list --category food     # filter by category
```

### View a summary of all expenses
```bash
python main.py summary
```
Shows the running total plus a breakdown by category.

### View a summary for a specific month (current year by default)
```bash
python main.py summary --month 8
python main.py summary --month 8 --year 2025   # a different year
python main.py summary --month 8 --category food
```
If a budget is set for that month, the remaining budget and an
over-budget warning (if applicable) are shown automatically.

### Set a monthly budget
```bash
python main.py budget --month 8 --amount 500
```
Once set, adding/updating an expense in that month, or running
`summary --month 8`, will print a warning like:

```
⚠️  WARNING: You have exceeded your budget for August 2026! Spent: $612.00 / Budget: $500.00
```

### Export expenses to CSV
```bash
python main.py export
python main.py export --output my_expenses.csv
```

### Help
```bash
python main.py -h
python main.py add -h
```

## Design notes

- **Storage**: `expenses` table (id, date, description, amount, category)
  and `budgets` table (year, month, amount) in a single SQLite file.
- **Dates**: stored as `YYYY-MM-DD`; new expenses default to today's date.
- **Validation**: amounts must be > 0, descriptions can't be empty; the CLI
  prints a clear `Error: ...` message and exits with status 1 on bad input.
- **Categories**: free-text, lower-cased for consistent filtering
  (`Food` and `food` are treated the same).
- **Budgets**: one budget per (year, month); setting it again overwrites
  the previous value for that month.
