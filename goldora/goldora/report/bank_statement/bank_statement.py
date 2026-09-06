import frappe
from erpnext.accounts.report.general_ledger.general_ledger import execute as gl_execute
from erpnext.accounts.report.general_ledger.general_ledger import get_translated_labels_for_totals
from frappe import _

from goldora.remarks import strip_reference_line


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

	# GL's marker rows carry their (translated, quoted) label in `account`.
	marker_types = {label.strip("'"): key for key, label in get_translated_labels_for_totals().items()}

	rows = []
	for d in data:
		label = (d.get("account") or "").strip("'")
		row = {
			"posting_date": d.get("posting_date"),
			"debit": d.get("debit"),
			"credit": d.get("credit"),
			"balance": d.get("balance"),
			# marker rows carry their label in `account`, quoted by the GL report
			"remarks": strip_reference_line(d.get("remarks")) if d.get("posting_date") else label,
		}
		if d.get("posting_date"):
			row["row_type"] = "entry"
			row["voucher_type"] = d.get("voucher_type")
			row["voucher_no"] = d.get("voucher_no")
		else:
			# a marker row with an unknown label is GL's blank spacer — drop it
			if label not in marker_types:
				continue
			row["row_type"] = marker_types[label]
		rows.append(row)

	# skip_total_row: summing a running-balance column is meaningless — it produced a
	# 6.8M "closing balance" out of a 435K statement. Vetoes the Report doc's
	# add_total_row checkbox, which is how the bogus row got in.
	return get_columns(), rows, None, None, None, 1


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
			# full voucher names (ACC-JV-2026-00231) must not truncate — this is
			# the column the client identifies entries by
			"width": 200,
		},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Debit"), "fieldname": "debit", "fieldtype": "Currency", "width": 130},
		{"label": _("Credit"), "fieldname": "credit", "fieldtype": "Currency", "width": 130},
		{"label": _("Balance"), "fieldname": "balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Small Text", "width": 400},
	]
