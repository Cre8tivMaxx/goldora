import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

COMPANY = "_Test Company"
PRINT_FORMAT = "Goldora Journal Entry"


class TestJournalEntryPrintFormat(FrappeTestCase):
	"""The client asked for one default print format for Journal Entry with debit,
	credit, party type, party, a running total and the per-row user remark."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.expense = frappe.get_value(
			"Account",
			{"company": COMPANY, "is_group": 0, "root_type": "Expense", "account_type": ("!=", "Payable")},
			"name",
			order_by="creation",
		)
		cls.bank = frappe.get_value("Account", {"company": COMPANY, "account_type": "Bank"}, "name")

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = COMPANY
		je.posting_date = today()
		je.user_remark = "Header remark"
		je.append(
			"accounts",
			{"account": cls.expense, "debit_in_account_currency": 500, "user_remark": "Row remark A"},
		)
		je.append(
			"accounts",
			{"account": cls.bank, "credit_in_account_currency": 500, "user_remark": "Row remark B"},
		)
		je.insert(ignore_permissions=True)
		je.submit()
		cls.je_name = je.name

	def test_is_the_doctype_default(self):
		self.assertEqual(
			frappe.get_meta("Journal Entry").get("default_print_format"), PRINT_FORMAT
		)

	def test_renders_accounts_parties_remarks_and_totals(self):
		html = frappe.get_print("Journal Entry", self.je_name, PRINT_FORMAT)
		self.assertIn(self.expense, html)
		self.assertIn(self.bank, html)
		self.assertIn("Row remark A", html)
		self.assertIn("Row remark B", html)
		self.assertIn("500.00", html)

	def test_template_has_no_line_comment_inside_a_jinja_block(self):
		"""microtemplate.js collapses newlines before compiling, so a `//` comment
		inside a {% %} block eats the rest of the block silently (see 25bb3dd)."""
		html_source = frappe.db.get_value("Print Format", PRINT_FORMAT, "html")
		for block in re.findall(r"\{%.*?%\}", html_source, flags=re.S):
			self.assertNotIn("//", block)
