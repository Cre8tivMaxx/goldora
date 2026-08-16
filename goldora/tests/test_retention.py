import frappe
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class TestRetention(FrappeTestCase):
	def setUp(self):
		self.retention_account = "Retention Receivable - _TC"
		if not frappe.db.exists("Account", self.retention_account):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Retention Receivable",
					"parent_account": "Accounts Receivable - _TC",
					"company": "_Test Company",
					"account_type": "Receivable",
				}
			).insert()

		settings = frappe.get_single("Retention Settings")
		settings.retention_accounts = []
		settings.append(
			"retention_accounts", {"company": "_Test Company", "retention_account": self.retention_account}
		)
		settings.save()

	def test_retention_computed_on_net_total_and_reduces_outstanding(self):
		si = create_sales_invoice(do_not_save=True, qty=1, rate=1000)
		si.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account Service Tax - _TC",
				"description": "Service Tax",
				"rate": 15,
			},
		)
		si.custom_apply_retention = 1
		si.custom_retention_percent = 10
		si.insert()
		si.submit()
		si.reload()

		self.assertEqual(si.net_total, 1000)
		self.assertEqual(si.custom_retention_amount, 100)
		self.assertEqual(flt(si.outstanding_amount), flt(si.grand_total - 100))

		je_name = si.custom_retention_journal_entry
		self.assertTrue(je_name)

		gl_entry = frappe.db.get_value(
			"GL Entry",
			{"voucher_no": je_name, "account": self.retention_account, "party": si.customer},
			["debit", "party_type"],
			as_dict=True,
		)
		self.assertEqual(flt(gl_entry.debit), 100)
		self.assertEqual(gl_entry.party_type, "Customer")

		si.cancel()
		si.reload()
		self.assertFalse(si.custom_retention_journal_entry)
		self.assertEqual(flt(si.outstanding_amount), flt(si.grand_total))

		je = frappe.get_doc("Journal Entry", je_name)
		self.assertEqual(je.docstatus, 2)
