import re

import frappe
from erpnext.accounts.report.general_ledger.general_ledger import execute as gl_execute
from frappe import _


# journal_entry.py's create_remarks() always emits this as its own line, built
# from the translated "Reference #{0} dated {1}" template — the client doesn't
# want that boilerplate line in the printed statement. Build the pattern from
# _() at call time (not import time) so it matches whatever language the
# viewer's session is actually in.
def strip_reference_line(remarks):
	if not remarks:
		return remarks
	pattern = re.escape(_("Reference #{0} dated {1}")).replace(r"\{0\}", ".*?").replace(r"\{1\}", ".*?")
	reference_line_re = re.compile(r"^\s*" + pattern + r"\s*$", re.MULTILINE)
	return "\n".join(line for line in reference_line_re.sub("", remarks).splitlines() if line.strip())


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
			"remarks": strip_reference_line(d.get("remarks"))
			if d.get("posting_date")
			else (d.get("account") or "").strip("'"),
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
