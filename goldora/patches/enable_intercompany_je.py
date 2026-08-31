import frappe

from goldora.company import setup_intercompany


def execute():
	"""Turn on inter-company JE mirroring for every existing company, and repoint
	each company's suspense account to 1910 (previously an auto-created
	`حساب وسيط - شركات شقيقة` account with no fixed number). The old account is
	left in place, just unreferenced.
	"""
	if not frappe.db.has_column("Company", "custom_enable_intercompany_je"):
		# fixtures were skipped (bench migrate --skip-fixtures); nothing to set up yet
		return

	for name in frappe.get_all("Company", pluck="name"):
		frappe.db.set_value("Company", name, "custom_enable_intercompany_je", 1)
		setup_intercompany(frappe.get_doc("Company", name))
