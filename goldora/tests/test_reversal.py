import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from goldora.patches.backfill_reversed_journal_entries import execute as backfill

COMPANY = "_Test Company"


def _make_je(rows, remark="Test JE"):
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = COMPANY
	je.posting_date = today()
	je.user_remark = remark
	# intercompany is irrelevant here and would need its own setup
	je.custom_create_intercompany_je = 0
	for row in rows:
		je.append("accounts", row)
	je.insert(ignore_permissions=True)
	return je


class TestReversal(FrappeTestCase):
	def setUp(self):
		self.expense = frappe.get_value(
			"Account",
			{"company": COMPANY, "is_group": 0, "root_type": "Expense", "account_type": ("!=", "Payable")},
			"name",
			order_by="creation",
		)
		self.bank = frappe.get_value("Account", {"company": COMPANY, "account_type": "Bank"}, "name")

	def _submit_je(self):
		je = _make_je(
			[
				{"account": self.expense, "debit_in_account_currency": 100},
				{"account": self.bank, "credit_in_account_currency": 100},
			]
		)
		je.submit()
		return je

	def test_reversing_flags_the_original(self):
		original = self._submit_je()

		reversal = frappe.get_doc(make_reverse_journal_entry(original.name))
		reversal.posting_date = today()
		reversal.insert(ignore_permissions=True)
		reversal.submit()

		original.reload()
		self.assertTrue(original.custom_is_reversed)
		self.assertEqual(original.custom_reversed_by, reversal.name)

	def test_cancelling_the_reversal_clears_the_flag(self):
		original = self._submit_je()
		reversal = frappe.get_doc(make_reverse_journal_entry(original.name))
		reversal.posting_date = today()
		reversal.insert(ignore_permissions=True)
		reversal.submit()

		reversal.cancel()

		original.reload()
		self.assertFalse(original.custom_is_reversed)
		self.assertFalse(original.custom_reversed_by)

	def test_backfill_patch_restores_flags(self):
		original = self._submit_je()
		reversal = frappe.get_doc(make_reverse_journal_entry(original.name))
		reversal.posting_date = today()
		reversal.insert(ignore_permissions=True)
		reversal.submit()

		# simulate a pair reversed before the sync hook existed
		frappe.db.set_value(
			"Journal Entry", original.name, {"custom_is_reversed": 0, "custom_reversed_by": None}
		)

		backfill()

		original.reload()
		self.assertTrue(original.custom_is_reversed)
		self.assertEqual(original.custom_reversed_by, reversal.name)
