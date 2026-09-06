"""Drop the auto-generated reference boilerplate from remarks already written.

goldora.remarks.drop_reference_remark keeps it out of anything saved from now on,
but every row already in the ledger still carries it, and the General Ledger
report reads those rows raw. Only the remark *text* is rewritten -- never an
amount, account, party or date -- and only where stripping actually changes it.
"""

import frappe

from goldora.remarks import reference_prefixes, strip_reference_line

# GL Entry is what the General Ledger report reads; the other two are the sources
# it was copied from, kept in step so a resaved document doesn't reintroduce it.
TARGETS = (
	("GL Entry", "remarks"),
	("Journal Entry", "remark"),
	("Payment Entry", "remarks"),
)


def execute():
	for doctype, fieldname in TARGETS:
		if frappe.db.has_column(doctype, fieldname):
			_clean(doctype, fieldname)


def _clean(doctype, fieldname):
	table = f"tab{doctype}"
	prefixes = reference_prefixes()

	if prefixes:
		where = " OR ".join([f"`{fieldname}` LIKE %s"] * len(prefixes))
		values = [f"%{prefix}%" for prefix in prefixes]
	else:
		# no usable prefix to narrow on: fall back to every non-empty remark
		where, values = f"`{fieldname}` IS NOT NULL AND `{fieldname}` != ''", []

	rows = frappe.db.sql(
		f"SELECT `name`, `{fieldname}` AS `text` FROM `{table}` WHERE {where}", values, as_dict=True
	)

	changed = 0
	for row in rows:
		cleaned = strip_reference_line(row.text)
		if cleaned == row.text:
			continue
		# update_modified=False: this is boilerplate cleanup, not a real edit, and
		# these are submitted documents
		frappe.db.set_value(doctype, row.name, fieldname, cleaned, update_modified=False)
		changed += 1

	print(f"strip_reference_remarks: {doctype}.{fieldname} -- {changed} of {len(rows)} scanned rewritten")
