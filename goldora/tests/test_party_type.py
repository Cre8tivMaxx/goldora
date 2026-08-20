import frappe
from frappe.tests.utils import FrappeTestCase

from goldora.party_type import get_account_details_and_party_type


class TestDefaultPartyType(FrappeTestCase):
	def setUp(self):
		self.company = frappe.get_all("Company", limit=1, pluck="name")[0]
		self.today = frappe.utils.today()

	def get_account(self, account_type):
		return frappe.get_all(
			"Account",
			filters={"company": self.company, "account_type": account_type, "is_group": 0},
			limit=1,
			pluck="name",
		)[0]

	def test_custom_default_party_type_wins(self):
		account = self.get_account("Expense Account")
		frappe.db.set_value("Account", account, "custom_default_party_type", "Employee")
		frappe.clear_cache(doctype="Account")

		values = get_account_details_and_party_type(account, self.today, self.company)
		self.assertEqual(values["party_type"], "Employee")

	def test_falls_back_to_erpnext_default(self):
		account = self.get_account("Receivable")
		frappe.db.set_value("Account", account, "custom_default_party_type", None)
		frappe.clear_cache(doctype="Account")

		values = get_account_details_and_party_type(account, self.today, self.company)
		self.assertEqual(values["party_type"], "Customer")
