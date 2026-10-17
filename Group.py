"""Core susu (rotating savings) logic. No I/O in this module."""

from .money import format_amount


class SusuError(ValueError):
    """Raised for any rule violation; the message is safe to show to users."""


class SusuGroup:
    def __init__(self, name, weekly_amount):
        name = (name or "").strip()
        if not name:
            raise SusuError("Group name cannot be empty")
        if weekly_amount <= 0:
            raise SusuError("Weekly contribution must be greater than zero")
        self.name = name
        self.weekly_amount = weekly_amount  # pesewas
        self.members = []                   # payout order = join order
        self.week = 1                       # current open week (1-based)
        self.paid = {}                      # {member: pesewas paid this week}
        self.history = []                   # payout records

    # ---------- helpers ----------
    @property
    def pot(self):
        return self.weekly_amount * len(self.members)

    @property
    def complete(self):
        return bool(self.members) and self.week > len(self.members)

    def _find(self, name):
        """Case-insensitive lookup so 'ama' and 'Ama' are the same member."""
        key = (name or "").strip().lower()
        for m in self.members:
            if m.lower() == key:
                return m
        return None

    def _require_open(self):
        if self.complete:
            raise SusuError("The cycle is complete: every member has been paid")

    # ---------- operations ----------
    def add_member(self, name):
        name = (name or "").strip()
        if not name:
            raise SusuError("Member name cannot be empty")
        if self._find(name):
            raise SusuError(f"Member '{name}' already exists")
        # Assumption: the roster is locked once money has moved, so that the
        # pot size and payout order cannot change mid-cycle.
        if self.week > 1 or any(self.paid.values()):
            raise SusuError(
                "Members can only be added before any contribution is recorded"
            )
        self.members.append(name)
        self.paid[name] = 0

    def contribute(self, name, amount, week=None):
        member = self._find(name)
        if not member:
            raise SusuError(f"Unknown member '{name}'")
        if amount <= 0:
            raise SusuError("Contribution must be greater than zero")
        self._require_open()
        if week is not None and week != self.week:
            raise SusuError(
                f"Only the current week ({self.week}) is open; cannot record week {week}"
            )
        owed = self.weekly_amount - self.paid[member]
        if amount > owed:
            raise SusuError(
                f"{member} only owes {format_amount(owed)} for week {self.week}; "
                f"{format_amount(amount)} is too much"
            )
        self.paid[member] += amount
        return owed - amount  # remaining balance

    def outstanding(self):
        """{member: pesewas still owed this week} for members who owe > 0."""
        return {
            m: self.weekly_amount - self.paid[m]
            for m in self.members
            if self.paid[m] < self.weekly_amount
        }

    def close_week(self):
        """Pay out if everyone paid in full. Returns (closed, info).

        closed=True  -> info is the payout record
        closed=False -> info is the outstanding dict; nothing changes
        """
        self._require_open()
        if len(self.members) < 2:
            raise SusuError("A group needs at least 2 members before a week can close")
        owing = self.outstanding()
        if owing:
            return False, owing
        recipient = self.members[self.week - 1]
        record = {"week": self.week, "recipient": recipient, "amount": self.pot}
        self.history.append(record)
        self.week += 1
        self.paid = {m: 0 for m in self.members}
        return True, record

    # ---------- persistence ----------
    def to_dict(self):
        return {
            "name": self.name,
            "weekly_amount": self.weekly_amount,
            "members": self.members,
            "week": self.week,
            "paid": self.paid,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, d):
        g = cls(d["name"], d["weekly_amount"])
        g.members = list(d["members"])
        g.week = d["week"]
        g.paid = dict(d["paid"])
        g.history = list(d["history"])
        return g
