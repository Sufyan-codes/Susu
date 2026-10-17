# Susu Group Tracker

A small command-line program that manages a rotating savings group (susu).
Every member pays the same fixed amount each week; each week the whole pot goes
to one member, in the order they joined, until everyone has received it once.

Written in Python 3 using only the standard library. No installation needed.

## How to run

Requires Python 3.9+ (developed on 3.13).

```bash
# 1. Create a group: name and weekly contribution in GHS
python3 -m susu create "Friends" 50

# 2. Add members (payout order = the order you add them)
python3 -m susu add-member Ama
python3 -m susu add-member Kofi
python3 -m susu add-member Esi

# 3. Record contributions (partial payments allowed)
python3 -m susu pay Ama 50
python3 -m susu pay Kofi 50
python3 -m susu pay Esi 30

# 4. Try to close the week
python3 -m susu close-week      # Esi still owes GHS 20.00, no payout
python3 -m susu pay Esi 20
python3 -m susu close-week      # Ama receives GHS 150.00, week 2 begins

# 5. See where things stand
python3 -m susu report
```

Data is saved in `susu.json` in the current folder. Use `--file other.json`
(before the command) to keep several groups: `python3 -m susu --file a.json report`.

### Commands

| Command | Purpose |
|---|---|
| `create NAME AMOUNT [--force]` | Start a group with a fixed weekly contribution |
| `add-member NAME` | Add a member |
| `pay MEMBER AMOUNT [--week N]` | Record a (possibly partial) contribution |
| `close-week` | Pay out if everyone is fully paid, otherwise list who owes what |
| `report` | Current week, who has paid, who owes what, payout history |

Errors print `Error: ...` to stderr and exit with code 1.

## How to run the tests

```bash
python3 -m unittest -v
```

14 tests cover exact money handling, every validation rule, partial payments,
the "week cannot close" case, a full rotation to completion, and a CLI
round-trip through the data file.

## Design notes

- **Exact money.** Amounts are parsed with `decimal.Decimal` and stored as
  integer pesewas. Floats are never used. An amount with more than 2 decimal
  places (e.g. `1.005`) is rejected instead of rounded.
- `susu/group.py` holds all the rules and does no I/O, so it is easy to test.
  `susu/cli.py` handles arguments, the JSON file, and printing.
- The data file is written to a temp file and renamed, so a crash mid-save
  cannot corrupt it.

## Assumptions and decisions

The brief left these open, so here is what I chose:

1. **Payout order is join order.** First member added is paid in week 1.
2. **The roster locks once money moves.** Members can only be added before the
   first contribution is recorded. Adding someone later would change the pot
   size and unfairly reorder payouts. Attempts are rejected with a clear error.
3. **Contributions are only for the current week.** Past weeks are closed and
   future weeks are not open. `--week` is accepted but must equal the current
   week.
4. **A group needs at least 2 members** before a week can be closed.
5. **Names are case-insensitive** for uniqueness and lookup (`ama` = `Ama`).
   The spelling used when first added is what is displayed.
6. **Overpayment is rejected, not carried forward.** A member can never pay
   more than they still owe for the current week.
7. **The cycle ends after everyone has been paid once.** After the last payout
   the group is marked complete and no further payments or closes are allowed.
8. **Closing an incomplete week changes nothing.** It reports who owes what and
   leaves all balances and the week number untouched.
9. **Currency is GHS** and is only a display label; the maths is currency-agnostic.

## What I would improve with more time

- Allow late joiners with an explicit, agreed rule (e.g. joining at the end of
  the order, and catching up on missed contributions).
- A payment ledger with timestamps per contribution, not just a running total
  per week, for auditing and undo.
- Optional carry-over of overpayments into the next week.
- Multiple groups in one data file and an `--as-json` output for a small API.
- Concurrency protection (file locking) if two people run commands at once.
