import os
import tempfile
import unittest

from susu.cli import run
from susu.group import SusuError, SusuGroup
from susu.money import MoneyError, format_amount, parse_amount


def make_group(*names, amount="50"):
    g = SusuGroup("Test", parse_amount(amount))
    for n in names:
        g.add_member(n)
    return g


class MoneyTests(unittest.TestCase):
    def test_exact_parsing_no_float_errors(self):
        self.assertEqual(parse_amount("0.10"), 10)
        self.assertEqual(parse_amount("19.99"), 1999)
        self.assertEqual(parse_amount("50"), 5000)

    def test_rejects_sub_pesewa_and_garbage(self):
        for bad in ("1.005", "abc", "nan", "inf", ""):
            with self.assertRaises(MoneyError):
                parse_amount(bad)

    def test_format(self):
        self.assertEqual(format_amount(15000), "GHS 150.00")
        self.assertEqual(format_amount(5), "GHS 0.05")


class ValidationTests(unittest.TestCase):
    def test_duplicate_member_rejected_case_insensitive(self):
        g = make_group("Ama")
        with self.assertRaises(SusuError):
            g.add_member("ama")

    def test_unknown_member_rejected(self):
        g = make_group("Ama", "Kofi")
        with self.assertRaises(SusuError):
            g.contribute("Yaw", 5000)

    def test_zero_and_negative_rejected(self):
        g = make_group("Ama", "Kofi")
        for amt in (0, -100):
            with self.assertRaises(SusuError):
                g.contribute("Ama", amt)

    def test_overpayment_rejected_including_after_partial(self):
        g = make_group("Ama", "Kofi")
        with self.assertRaises(SusuError):
            g.contribute("Ama", 5001)
        g.contribute("Ama", 3000)
        with self.assertRaises(SusuError):
            g.contribute("Ama", 2001)  # only 20.00 left
        self.assertEqual(g.paid["Ama"], 3000)  # unchanged by failures


class WeekTests(unittest.TestCase):
    def test_spec_example(self):
        """Ama, Kofi, Esi at GHS 50: Esi pays 30, close fails, then completes."""
        g = make_group("Ama", "Kofi", "Esi")
        g.contribute("Ama", 5000)
        g.contribute("Kofi", 5000)
        g.contribute("Esi", 3000)
        closed, owing = g.close_week()
        self.assertFalse(closed)
        self.assertEqual(owing, {"Esi": 2000})
        self.assertEqual(g.week, 1)
        self.assertEqual(g.history, [])
        g.contribute("Esi", 2000)
        closed, rec = g.close_week()
        self.assertTrue(closed)
        self.assertEqual(rec, {"week": 1, "recipient": "Ama", "amount": 15000})
        self.assertEqual(g.week, 2)
        self.assertEqual(g.outstanding(), {m: 5000 for m in g.members})

    def test_partial_payments_accumulate_exactly(self):
        g = make_group("Ama", "Kofi", amount="0.30")
        for _ in range(3):
            g.contribute("Ama", 10)  # three payments of 0.10
        self.assertEqual(g.paid["Ama"], 30)
        self.assertNotIn("Ama", g.outstanding())

    def test_full_rotation_and_completion(self):
        g = make_group("Ama", "Kofi")
        for expected in ("Ama", "Kofi"):
            for m in g.members:
                g.contribute(m, 5000)
            _, rec = g.close_week()
            self.assertEqual(rec["recipient"], expected)
            self.assertEqual(rec["amount"], 10000)
        self.assertTrue(g.complete)
        with self.assertRaises(SusuError):
            g.contribute("Ama", 5000)
        with self.assertRaises(SusuError):
            g.close_week()

    def test_cannot_pay_for_other_week(self):
        g = make_group("Ama", "Kofi")
        with self.assertRaises(SusuError):
            g.contribute("Ama", 5000, week=2)

    def test_member_added_after_start_rejected(self):
        g = make_group("Ama", "Kofi")
        g.contribute("Ama", 100)
        with self.assertRaises(SusuError):
            g.add_member("Esi")

    def test_cannot_close_with_fewer_than_two_members(self):
        g = make_group("Ama")
        with self.assertRaises(SusuError):
            g.close_week()


class PersistenceTests(unittest.TestCase):
    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            f = os.path.join(d, "s.json")
            lines = []
            def cmd(*a):
                run(["--file", f, *a], out=lines.append)
            cmd("create", "Friends", "50")
            cmd("add-member", "Ama")
            cmd("add-member", "Kofi")
            cmd("pay", "Ama", "50")
            cmd("pay", "Kofi", "20.50")
            cmd("close-week")
            self.assertIn("Cannot close", lines[-2])
            self.assertIn("GHS 29.50", lines[-1])
            cmd("pay", "Kofi", "29.50")
            cmd("close-week")
            self.assertIn("Ama receives GHS 100.00", lines[-2])
            cmd("report")
            self.assertIn("Week 1: Ama received GHS 100.00", lines[-1])


if __name__ == "__main__":
    unittest.main()
