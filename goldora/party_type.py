import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import (
	get_account_details_and_party_type as _erpnext_get_account_details_and_party_type,
)


@frappe.whitelist()
def get_account_details_and_party_type(account, date, company, debit=None, credit=None, exchange_rate=None):
	"""ERPNext only maps Receivable->Customer and Payable->Supplier.

	Let any account name its own default party type via custom_default_party_type.
	"""
	values = _erpnext_get_account_details_and_party_type(
		account, date, company, debit=debit, credit=credit, exchange_rate=exchange_rate
	)
	if not values:
		return values

	party_type = frappe.get_cached_value("Account", account, "custom_default_party_type")
	if party_type:
		values["party_type"] = party_type
		values.pop("party", None)

	return values
