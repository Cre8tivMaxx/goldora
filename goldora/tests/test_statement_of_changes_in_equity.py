import frappe
from frappe.tests.utils import FrappeTestCase

from goldora.goldora.report.statement_of_changes_in_equity.statement_of_changes_in_equity import (
	_movement_label,
	execute,
)


class TestStatementOfChangesInEquity(FrappeTestCase):
	"""Posts known amounts to a throwaway equity account so every figure in that
	account's column can be asserted against the amount actually posted."""

	def setUp(self):
		self.company = frappe.get_all("Company", limit=1, pluck="name")[0]
		self.cash = frappe.get_all(
			"Account",
			filters={"company": self.company, "account_type": ["in", ["Bank", "Cash"]], "is_group": 0},
			limit=1,
			pluck="name",
		)[0]
		self.equity = self.make_equity_account()

	def make_equity_account(self):
		parent = frappe.get_all(
			"Account",
			filters={"company": self.company, "root_type": "Equity", "is_group": 1},
			order_by="lft desc",
			limit=1,
			pluck="name",
		)[0]
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": f"Goldora SOCIE Test {frappe.generate_hash(length=8)}",
				"parent_account": parent,
				"company": self.company,
				"root_type": "Equity",
				"is_group": 0,
			}
		)
		account.insert()
		return account.name

	def make_je(self, posting_date, credit_equity):
		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": posting_date,
				"accounts": [
					{"account": self.equity, "credit_in_account_currency": credit_equity},
					{"account": self.cash, "debit_in_account_currency": credit_equity},
				],
			}
		)
		je.insert()
		je.submit()
		return je

	def run_report(self):
		columns, rows = execute({"company": self.company, "from_date": "2026-06-01", "to_date": "2026-06-30"})
		fieldname = next(c["fieldname"] for c in columns if c["label"] == self.equity)
		return columns, rows, fieldname

	def test_opening_and_movement_match_what_was_posted(self):
		self.make_je("2026-01-05", 300000)  # before the period -> opening
		self.make_je("2026-06-10", 10000)  # inside the period -> movement

		_columns, rows, field = self.run_report()

		self.assertEqual(rows[0]["particulars"], "Opening Balance")
		self.assertAlmostEqual(rows[0][field], 300000, places=2)

		movements = rows[1:-1]
		self.assertEqual([r["particulars"] for r in movements], [self.cash])
		self.assertAlmostEqual(movements[0][field], 10000, places=2)

		self.assertEqual(rows[-1]["particulars"], "Closing Balance")
		self.assertAlmostEqual(rows[-1][field], 310000, places=2)

	def test_entries_outside_the_period_are_excluded_from_movements(self):
		self.make_je("2026-06-10", 10000)
		self.make_je("2026-07-10", 55000)  # after the period

		_columns, rows, field = self.run_report()
		self.assertAlmostEqual(rows[-1][field], 10000, places=2)

	def test_total_column_is_the_row_sum(self):
		self.make_je("2026-06-10", 10000)
		columns, rows, _field = self.run_report()
		account_fields = [c["fieldname"] for c in columns if c["fieldname"] not in ("particulars", "total")]
		for row in rows:
			self.assertAlmostEqual(sum(row[f] for f in account_fields), row["total"], places=2)

	def test_movement_label_is_order_independent(self):
		# GL Entry.against joins a set(), so the same counter accounts can arrive
		# in either order and must still land on one row
		self.assertEqual(_movement_label("Cash - G, Bank - G"), _movement_label("Bank - G, Cash - G"))
		self.assertEqual(_movement_label("Cash - G"), "Cash - G")
		self.assertEqual(_movement_label(""), "Other")
		self.assertEqual(_movement_label(None), "Other")
