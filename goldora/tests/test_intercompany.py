import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, today

from goldora.company import setup_intercompany

COMPANY_A = "_Test Company"
COMPANY_B = "_Test Company with perpetual inventory"


def _make_je(company, rows, remark="Test JE"):
	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = company
	je.posting_date = today()
	je.user_remark = remark
	for row in rows:
		je.append("accounts", row)
	je.insert(ignore_permissions=True)
	return je


class TestIntercompany(FrappeTestCase):
	def setUp(self):
		# both companies need their internal parties and suspense account; without them
		# every "counterpart created" assertion fails for a setup reason, not a bug
		setup_intercompany(frappe.get_doc("Company", COMPANY_A))
		setup_intercompany(frappe.get_doc("Company", COMPANY_B))
		frappe.clear_cache()

		self.customer_b_in_a = frappe.db.get_value(
			"Customer", {"represents_company": COMPANY_B}, "name"
		)
		self.expense_a = frappe.get_value(
			"Account",
			{"company": COMPANY_A, "is_group": 0, "root_type": "Expense", "account_type": ("!=", "Payable")},
			"name",
			order_by="creation",
		)
		self.receivable_a = frappe.get_cached_value("Company", COMPANY_A, "default_receivable_account")
		self.bank_a = frappe.get_value("Account", {"company": COMPANY_A, "account_type": "Bank"}, "name")
		self.suspense_b = frappe.get_cached_value(
			"Company", COMPANY_B, "custom_intercompany_suspense_account"
		)
		self.payable_b = frappe.get_cached_value("Company", COMPANY_B, "default_payable_account")

	def test_happy_path_mirrors_only_party_row(self):
		je = _make_je(
			COMPANY_A,
			[
				{
					"account": self.receivable_a,
					"party_type": "Customer",
					"party": self.customer_b_in_a,
					"debit_in_account_currency": 8400,
				},
				{
					"account": self.expense_a,
					"credit_in_account_currency": 1.15,
				},
				{
					"account": self.bank_a,
					"credit_in_account_currency": 8398.85,
				},
			],
		)
		je.submit()
		je.reload()

		counterpart_name = je.inter_company_journal_entry_reference
		self.assertTrue(counterpart_name)
		counterpart = frappe.get_doc("Journal Entry", counterpart_name)
		self.assertEqual(counterpart.company, COMPANY_B)
		self.assertEqual(counterpart.docstatus, 0)

		payable_row = next(r for r in counterpart.accounts if r.account == self.payable_b)
		self.assertEqual(flt(payable_row.credit_in_account_currency), 8400)
		self.assertNotEqual(flt(payable_row.credit_in_account_currency), 8401.15)
		suspense_row = next(r for r in counterpart.accounts if r.account == self.suspense_b)
		self.assertEqual(flt(suspense_row.debit_in_account_currency), 8400)

	def test_no_intercompany_party_creates_nothing(self):
		je = _make_je(
			COMPANY_A,
			[
				{"account": self.expense_a, "debit_in_account_currency": 100},
				{"account": self.bank_a, "credit_in_account_currency": 100},
			],
		)
		je.submit()
		je.reload()
		self.assertFalse(je.inter_company_journal_entry_reference)

	def test_checkbox_off_skips_counterpart(self):
		je = _make_je(
			COMPANY_A,
			[
				{
					"account": self.receivable_a,
					"party_type": "Customer",
					"party": self.customer_b_in_a,
					"debit_in_account_currency": 500,
				},
				{"account": self.bank_a, "credit_in_account_currency": 500},
			],
		)
		je.custom_create_intercompany_je = 0
		je.save()
		je.submit()
		je.reload()
		self.assertFalse(je.inter_company_journal_entry_reference)

	def test_recursion_guard_counterpart_spawns_nothing(self):
		je = _make_je(
			COMPANY_A,
			[
				{
					"account": self.receivable_a,
					"party_type": "Customer",
					"party": self.customer_b_in_a,
					"debit_in_account_currency": 200,
				},
				{"account": self.bank_a, "credit_in_account_currency": 200},
			],
		)
		je.submit()
		je.reload()
		counterpart = frappe.get_doc("Journal Entry", je.inter_company_journal_entry_reference)
		# balance the draft counterpart's suspense leg onto a real account and submit it
		for row in counterpart.accounts:
			if row.account == self.suspense_b:
				row.account = self.payable_b
				row.credit_in_account_currency, row.debit_in_account_currency = (
					row.debit_in_account_currency,
					row.credit_in_account_currency,
				)
		counterpart.save()
		counterpart.submit()
		counterpart.reload()
		self.assertFalse(counterpart.inter_company_journal_entry_reference)

	def test_cancel_with_draft_counterpart_deletes_it(self):
		je = _make_je(
			COMPANY_A,
			[
				{
					"account": self.receivable_a,
					"party_type": "Customer",
					"party": self.customer_b_in_a,
					"debit_in_account_currency": 300,
				},
				{"account": self.bank_a, "credit_in_account_currency": 300},
			],
		)
		je.submit()
		je.reload()
		counterpart_name = je.inter_company_journal_entry_reference

		je.cancel()
		je.reload()
		self.assertFalse(je.inter_company_journal_entry_reference)
		self.assertFalse(frappe.db.exists("Journal Entry", counterpart_name))

	def test_missing_suspense_account_warns_and_skips(self):
		suspense = frappe.get_cached_value("Company", COMPANY_B, "custom_intercompany_suspense_account")
		frappe.db.set_value("Company", COMPANY_B, "custom_intercompany_suspense_account", None)
		frappe.clear_cache()
		try:
			je = _make_je(
				COMPANY_A,
				[
					{
						"account": self.receivable_a,
						"party_type": "Customer",
						"party": self.customer_b_in_a,
						"debit_in_account_currency": 150,
					},
					{"account": self.bank_a, "credit_in_account_currency": 150},
				],
			)
			je.submit()
			je.reload()
			self.assertFalse(je.inter_company_journal_entry_reference)
		finally:
			frappe.db.set_value("Company", COMPANY_B, "custom_intercompany_suspense_account", suspense)
			frappe.clear_cache()
	def test_cancelling_submitted_counterpart_keeps_the_source(self):
		je = _make_je(
			COMPANY_A,
			[
				{
					"account": self.receivable_a,
					"party_type": "Customer",
					"party": self.customer_b_in_a,
					"debit_in_account_currency": 400,
				},
				{"account": self.bank_a, "credit_in_account_currency": 400},
			],
		)
		je.submit()
		je.reload()

		counterpart = frappe.get_doc("Journal Entry", je.inter_company_journal_entry_reference)
		for row in counterpart.accounts:
			if row.account == self.suspense_b:
				row.account = self.payable_b
				row.party_type, row.party = "Supplier", counterpart.accounts[0].party
		counterpart.save()
		counterpart.submit()

		# the link is symmetric; cancelling the counterpart must not touch the source
		counterpart.cancel()
		self.assertTrue(frappe.db.exists("Journal Entry", je.name))
		self.assertEqual(frappe.db.get_value("Journal Entry", je.name, "docstatus"), 1)
