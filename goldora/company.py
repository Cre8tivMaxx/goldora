import frappe
from frappe import _

SUSPENSE_ACCOUNT_NAME = "افتتاحي مؤقت"
SUSPENSE_ACCOUNT_NUMBER = "1910"
SUSPENSE_PARENT_ACCOUNT_NUMBER = "1900"
# "Current Assets" is the standard English CoA template's name for this group;
# "حسابات مؤقتة" is the same group's name in the Arabic CoA templates already in
# use here (see e.g. ZAD's "1900 - حسابات مؤقتة"). Companies whose CoA has neither
# still get skipped with a message rather than guessing at a wrong parent.
SUSPENSE_PARENT_ACCOUNT_NAMES = ("Current Assets", "حسابات مؤقتة")


def setup_intercompany(doc, method=None):
	"""Give a company the internal parties and suspense account inter-company JEs
	need. Hooked on on_update (not after_insert) because ERPNext's own
	Company.on_update is what creates the chart of accounts — at after_insert time
	no Account rows exist yet. Idempotent; runs on every Company save."""
	_setup_internal_party(doc, "Customer")
	_setup_internal_party(doc, "Supplier")
	_setup_suspense_account(doc)


def setup_all_intercompany():
	"""after_migrate: idempotent, runs after fixtures sync so the custom fields exist."""
	for name in frappe.get_all("Company", pluck="name"):
		setup_intercompany(frappe.get_doc("Company", name))


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
	existing = frappe.db.get_value(
		"Account",
		{"account_number": SUSPENSE_ACCOUNT_NUMBER, "company": doc.name, "is_group": 0},
		"name",
	)
	if not existing:
		parent = frappe.db.get_value(
			"Account",
			{"company": doc.name, "account_number": SUSPENSE_PARENT_ACCOUNT_NUMBER, "is_group": 1},
			"name",
		) or frappe.db.get_value(
			"Account",
			{"company": doc.name, "account_name": ("in", SUSPENSE_PARENT_ACCOUNT_NAMES), "is_group": 1},
			"name",
		)
		if not parent:
			message = _(
				"Could not find a parent group for account {0} in {1}; set the Inter-company Suspense Account manually."
			).format(SUSPENSE_ACCOUNT_NUMBER, doc.name)
			# msgprint is invisible from bench migrate; also print so it shows in the console
			frappe.msgprint(message)
			print(message)
			return

		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": SUSPENSE_ACCOUNT_NAME,
				"account_number": SUSPENSE_ACCOUNT_NUMBER,
				"parent_account": parent,
				"company": doc.name,
				"account_type": "",
			}
		)
		account.insert(ignore_permissions=True)
		existing = account.name

	frappe.db.set_value("Company", doc.name, "custom_intercompany_suspense_account", existing)
	doc.custom_intercompany_suspense_account = existing
