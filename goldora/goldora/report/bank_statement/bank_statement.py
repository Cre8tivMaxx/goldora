import frappe
from erpnext.accounts.report.general_ledger.general_ledger import execute as gl_execute
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	# no categorize_by => flat rows (one per GL line, each keeping its own remark)
	# plus a single opening / total / closing. Consolidation is what merged the
	# remarks in the report this replaces.
	filters.pop("categorize_by", None)
	filters.pop("group_by", None)
	filters.show_remarks = 1
	# the GL report iterates filters.account, so a single Link value must be wrapped
	if isinstance(filters.get("account"), str):
		filters.account = [filters.account]

	_columns, data = gl_execute(filters)

	rows = []
	for d in data:
		row = {
			"posting_date": d.get("posting_date"),
			"debit": d.get("debit"),
			"credit": d.get("credit"),
			"balance": d.get("balance"),
			# marker rows carry their label in `account`, quoted by the GL report
			"remarks": d.get("remarks") if d.get("posting_date") else (d.get("account") or "").strip("'"),
		}
		if d.get("posting_date"):
			row["voucher_type"] = d.get("voucher_type")
			row["voucher_no"] = d.get("voucher_no")
		rows.append(row)

	return get_columns(), rows


def get_columns():
	return [
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 0,
			"hidden": 1,
		},
		{
			"label": _("Serial"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 150,
		},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 130},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 130},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Small Text", "width": 400},
	]
