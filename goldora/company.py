import frappe
from frappe import _

SUSPENSE_ACCOUNT_NAME = "حساب وسيط - شركات شقيقة"


def setup_intercompany(doc, method=None):
	"""Give a company the internal parties and suspense account inter-company JEs
	need. Hooked on on_update (not after_insert) because ERPNext's own
	Company.on_update is what creates the chart of accounts — at after_insert time
	no Account rows exist yet. Idempotent; runs on every Company save."""
	_setup_internal_party(doc, "Customer")
	_setup_internal_party(doc, "Supplier")
	_setup_suspense_account(doc)


_PARTY_FIELDS = {
	"Customer": ("customer_name", "is_internal_customer", "customer_type"),
	"Supplier": ("supplier_name", "is_internal_supplier", "supplier_type"),
}


def _setup_internal_party(doc, party_type):
	name_field, internal_field, type_field = _PARTY_FIELDS[party_type]

	if frappe.db.get_value(party_type, {"represents_company": doc.name}, "name"):
		return

	existing = frappe.db.get_value(
		party_type, {name_field: doc.company_name, "represents_company": ("in", ("", None))}, "name"
	)
	if existing:
		# save() rather than db.set_value so ERPNext's internal-party validation runs
		# and represents_company's unique constraint surfaces as a friendly message
		party = frappe.get_doc(party_type, existing)
		party.update({internal_field: 1, "represents_company": doc.name})
		party.save(ignore_permissions=True)
		return

	frappe.get_doc(
		{
			"doctype": party_type,
			name_field: doc.company_name,
			type_field: "Company",
			internal_field: 1,
			"represents_company": doc.name,
		}
	).insert(ignore_permissions=True)


def _setup_suspense_account(doc):
	if doc.get("custom_intercompany_suspense_account"):
		return

	existing = frappe.db.get_value(
		"Account", {"account_name": SUSPENSE_ACCOUNT_NAME, "company": doc.name}, "name"
	)
	if not existing:
		current_assets = frappe.db.get_value(
			"Account", {"company": doc.name, "account_name": "Current Assets", "is_group": 1}, "name"
		)
		if not current_assets:
			frappe.msgprint(
				_("Could not find a Current Assets group for {0}; set the Inter-company Suspense Account manually.").format(
					doc.name
				)
			)
			return

		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": SUSPENSE_ACCOUNT_NAME,
				"parent_account": current_assets,
				"company": doc.name,
				"account_type": "",
			}
		)
		account.insert(ignore_permissions=True)
		existing = account.name

	frappe.db.set_value("Company", doc.name, "custom_intercompany_suspense_account", existing)
	doc.custom_intercompany_suspense_account = existing
