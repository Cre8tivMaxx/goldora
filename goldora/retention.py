import frappe
from frappe import _
from frappe.utils import flt


def get_retention_account(company: str) -> str:
	settings = frappe.get_cached_doc("Retention Settings")
	for row in settings.retention_accounts:
		if row.company == company:
			return row.retention_account

	frappe.throw(_("Set a Retention Account for company {0} in Retention Settings").format(company))


@frappe.whitelist()
def get_retention_companies() -> list[str]:
	settings = frappe.get_cached_doc("Retention Settings")
	return [row.company for row in settings.retention_accounts if row.retention_account]


def calculate(doc, method=None):
	if doc.is_return or not doc.get("custom_apply_retention"):
		doc.custom_retention_percent = 0
		doc.custom_retention_amount = 0
		return

	get_retention_account(doc.company)  # throws if company has no retention account configured

	if not (0 < flt(doc.custom_retention_percent) <= 100):
		frappe.throw(_("Retention Percent must be between 0 and 100"))

	doc.custom_retention_amount = flt(
		doc.net_total * doc.custom_retention_percent / 100,
		doc.precision("custom_retention_amount"),
	)


def book(doc, method=None):
	if doc.is_return or not doc.get("custom_apply_retention") or flt(doc.custom_retention_amount) <= 0:
		return

	retention_account = get_retention_account(doc.company)
	amount = flt(
		doc.base_net_total * doc.custom_retention_percent / 100,
		doc.precision("custom_retention_amount"),
	)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.company = doc.company
	je.posting_date = doc.posting_date
	je.user_remark = _("Retention withheld against Sales Invoice {0}").format(doc.name)
	je.append(
		"accounts",
		{
			"account": retention_account,
			"party_type": "Customer",
			"party": doc.customer,
			"debit_in_account_currency": amount,
			"credit_in_account_currency": 0,
			"cost_center": doc.get("cost_center"),
		},
	)
	je.append(
		"accounts",
		{
			"account": doc.debit_to,
			"party_type": "Customer",
			"party": doc.customer,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": amount,
			"reference_type": "Sales Invoice",
			"reference_name": doc.name,
			"cost_center": doc.get("cost_center"),
		},
	)
	je.insert(ignore_permissions=True)
	je.submit()

	doc.db_set("custom_retention_journal_entry", je.name)


def unbook(doc, method=None):
	je_name = doc.get("custom_retention_journal_entry")
	if not je_name:
		return

	if frappe.db.exists("Journal Entry", je_name):
		je = frappe.get_doc("Journal Entry", je_name)
		if je.docstatus == 1:
			je.cancel()

	doc.db_set("custom_retention_journal_entry", None)
