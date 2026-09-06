import re
from pathlib import Path
from unittest.mock import patch

import frappe
from erpnext.accounts.report.general_ledger.general_ledger import get_translated_labels_for_totals
from frappe.tests.utils import FrappeTestCase

from goldora.goldora.report.bank_statement.bank_statement import execute


class TestRowTypes(FrappeTestCase):
	"""The print template picks the Closing Balance box off the row tagged
	`closing`. It used to take the last row, which the datatable's own appended
	total row (a sum of every balance, including the markers) silently became."""

	def _result(self):
		labels = get_translated_labels_for_totals()
		gl_data = [
			frappe._dict(account=labels["opening"], debit=300091.53, credit=0, balance=300091.53),
			frappe._dict(
				posting_date="2026-08-27",
				voucher_type="Journal Entry",
				voucher_no="ACC-JV-2026-00265",
				debit=0,
				credit=35000.0,
				balance=265091.53,
				remarks="Reference #x dated 2026-08-27\nسكن د عماد",
			),
			# GL emits blank spacer rows with no label at all
			frappe._dict(debit_in_transaction_currency=None, credit_in_transaction_currency=None),
			frappe._dict(account=labels["total"], debit=0, credit=35000.0, balance=-35000.0),
			frappe._dict(account=labels["closing"], debit=300091.53, credit=35000.0, balance=265091.53),
		]
		with patch(
			"goldora.goldora.report.bank_statement.bank_statement.gl_execute",
			return_value=([], gl_data),
		):
			return execute({"account": "1201 - Bank"})

	def test_tags_every_row(self):
		self.assertEqual([r["row_type"] for r in self._result()[1]], ["opening", "entry", "total", "closing"])

	def test_closing_row_carries_the_final_balance(self):
		closing = [r for r in self._result()[1] if r["row_type"] == "closing"]
		self.assertEqual(len(closing), 1)
		self.assertEqual(closing[0]["balance"], 265091.53)

	def test_entry_keeps_voucher_and_stripped_remark(self):
		entry = next(r for r in self._result()[1] if r["row_type"] == "entry")
		self.assertEqual(entry["voucher_no"], "ACC-JV-2026-00265")
		self.assertEqual(entry["remarks"], "سكن د عماد")

	def test_vetoes_the_datatable_total_row(self):
		# summing a running balance is meaningless; skip_total_row is the 6th
		# return value frappe checks before honouring the report's add_total_row
		self.assertEqual(self._result()[5], 1)


class TestPrintTemplate(FrappeTestCase):
	"""frappe.template.compile collapses every newline to a space before compiling
	(frappe/public/js/frappe/microtemplate.js), so a // comment inside a {% %} block
	comments out the rest of that block. The template then compiles but throws
	"... is not defined" at render time, which reaches the user as the Print button
	doing nothing at all -- no dialog, no error. Block comments only."""

	def test_no_line_comments_in_code_blocks(self):
		template = (
			Path(__file__).parent.parent / "goldora/report/bank_statement/bank_statement.html"
		).read_text()

		# {% ... %} is a code block; {%= ... %} just interpolates
		for block in re.findall(r"\{%(?!=)(.*?)%\}", template, re.DOTALL):
			self.assertNotIn("//", re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL))
