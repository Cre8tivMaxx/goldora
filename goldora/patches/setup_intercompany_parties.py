import frappe

from goldora.company import setup_intercompany


def execute():
	"""One-time setup of inter-company parties/suspense accounts for companies that
	already existed before the inter-company JE feature. New companies get this via
	Company.on_update -> goldora.company.setup_intercompany.

	Idempotent, but registered in patches.txt rather than after_migrate so it does
	not re-claim parties on every migrate.
	"""
	if not frappe.db.has_column("Company", "custom_intercompany_suspense_account"):
		# fixtures were skipped (bench migrate --skip-fixtures); nothing to set up yet
		return

	for name in frappe.get_all("Company", pluck="name"):
		setup_intercompany(frappe.get_doc("Company", name))
