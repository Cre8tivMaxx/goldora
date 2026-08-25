import re

import frappe
from erpnext.accounts.report.general_ledger.general_ledger import execute as gl_execute
from frappe import _
from frappe.translate import get_all_translations
from frappe.utils.caching import request_cache

REFERENCE_TEMPLATE = "Reference #{0} dated {1}"


# The remark is frozen at Journal Entry creation time in the creating user's
# language, not the viewer's — an Arabic remark read from an English session
# never matched the session-language pattern. This site is English + Arabic, so
# match both.
@request_cache
def _reference_line_patterns():
	variants = {REFERENCE_TEMPLATE, get_all_translations("ar").get(REFERENCE_TEMPLATE, REFERENCE_TEMPLATE)}
	return [
		re.compile(
			r"^\s*" + re.escape(v).replace(r"\{0\}", ".*?").replace(r"\{1\}", ".*?") + r"\s*$",
			re.MULTILINE,
		)
		for v in variants
	]


# journal_entry.py's create_remarks() always emits this as its own line — the
# client doesn't want that boilerplate in the printed statement, only the note.
def strip_reference_line(remarks):
	if not remarks:
		return remarks
	for pattern in _reference_line_patterns():
		remarks = pattern.sub("", remarks)
	return "\n".join(line for line in remarks.splitlines() if line.strip())


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
