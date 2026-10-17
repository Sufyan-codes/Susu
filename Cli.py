"""Command-line interface. State is kept in a JSON file between commands."""

import argparse
import json
import os
import sys
import tempfile

from .group import SusuError, SusuGroup
from .money import MoneyError, format_amount, parse_amount

DEFAULT_FILE = "susu.json"


def load(path):
    if not os.path.exists(path):
        raise SusuError(f"No group found in '{path}'. Run 'create' first.")
    with open(path) as f:
        return SusuGroup.from_dict(json.load(f))


def save(group, path):
    # Write to a temp file then rename, so a crash can't corrupt the data.
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(group.to_dict(), f, indent=2)
    os.replace(tmp, path)


def report(g):
    lines = [f"Group: {g.name}", f"Weekly contribution: {format_amount(g.weekly_amount)}"]
    lines.append(f"Members ({len(g.members)}): " + (", ".join(g.members) or "none"))
    if g.complete:
        lines.append("Status: cycle complete, every member has been paid")
    else:
        lines.append(f"Current week: {g.week} of {len(g.members) or '?'}")
        if g.members and g.week <= len(g.members):
            lines.append(f"Next recipient: {g.members[g.week - 1]}  (pot {format_amount(g.pot)})")
        owing = g.outstanding()
        paid_up = [m for m in g.members if m not in owing]
        lines.append("Paid in full: " + (", ".join(paid_up) or "nobody yet"))
        if owing:
            lines.append("Still owes:")
            for m, amt in owing.items():
                lines.append(f"  - {m}: {format_amount(amt)}")
    lines.append("Payout history:")
    if g.history:
        for h in g.history:
            lines.append(f"  Week {h['week']}: {h['recipient']} received {format_amount(h['amount'])}")
    else:
        lines.append("  (none yet)")
    return "\n".join(lines)


def build_parser():
    p = argparse.ArgumentParser(prog="susu", description="Susu group tracker")
    p.add_argument("--file", default=DEFAULT_FILE, help="data file (default: susu.json)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="create a group")
    c.add_argument("name")
    c.add_argument("amount", help="weekly contribution in GHS, e.g. 50 or 50.00")
    c.add_argument("--force", action="store_true", help="overwrite an existing data file")

    a = sub.add_parser("add-member", help="add a member (payout order = order added)")
    a.add_argument("member")

    r = sub.add_parser("pay", help="record a contribution")
    r.add_argument("member")
    r.add_argument("amount")
    r.add_argument("--week", type=int, help="must be the current week if given")

    sub.add_parser("close-week", help="close the week and pay out if everyone paid")
    sub.add_parser("report", help="show current week and payout history")
    return p


def run(argv, out=print):
    args = build_parser().parse_args(argv)
    if args.cmd == "create":
        if os.path.exists(args.file) and not args.force:
            raise SusuError(f"'{args.file}' already exists (use --force to overwrite)")
        g = SusuGroup(args.name, parse_amount(args.amount))
        save(g, args.file)
        out(f"Created '{g.name}' with weekly contribution {format_amount(g.weekly_amount)}")
        return

    g = load(args.file)
    if args.cmd == "add-member":
        g.add_member(args.member)
        save(g, args.file)
        out(f"Added {args.member.strip()} (position {len(g.members)})")
    elif args.cmd == "pay":
        left = g.contribute(args.member, parse_amount(args.amount), args.week)
        save(g, args.file)
        out("Recorded. " + ("Paid in full." if left == 0 else f"Still owes {format_amount(left)}."))
    elif args.cmd == "close-week":
        closed, info = g.close_week()
        if closed:
            save(g, args.file)
            out(f"Week {info['week']} closed. {info['recipient']} receives {format_amount(info['amount'])}.")
            out("Cycle complete." if g.complete else f"Week {g.week} begins.")
        else:
            out("Cannot close the week yet. No payout made. Still owing:")
            for m, amt in info.items():
                out(f"  - {m}: {format_amount(amt)}")
    elif args.cmd == "report":
        out(report(g))


def main(argv=None):
    try:
        run(sys.argv[1:] if argv is None else argv)
    except (SusuError, MoneyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
