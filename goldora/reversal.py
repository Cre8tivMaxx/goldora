"""Keep the original Journal Entry's reversed-flag in step with its reversal.

erpnext.accounts.doctype.journal_entry.journal_entry.make_reverse_journal_entry
writes `reversal_of` only on the *reversing* entry; the original never learns it
has been reversed. This mirrors that link back onto the original so it can be
listed/filtered on (custom_is_reversed) and jumped to (custom_reversed_by).
"""

import frappe


def refresh(name):
	# Read the DB, not a document: lifecycle hooks run after their docstatus change.
	# A normal reversal wins; otherwise use the oldest live inter-company counterpart.
	live_reversal = frappe.db.get_value(
		"Journal Entry", {"reversal_of": name, "docstatus": 1}, "name"
	)
	live_counterpart = live_reversal or frappe.db.get_value(
		"Journal Entry",
		{
			"inter_company_journal_entry_reference": name,
			"creation": (">", frappe.db.get_value("Journal Entry", name, "creation")),
			"docstatus": ("<", 2),
		},
		"name",
		order_by="creation",
	)

	frappe.db.set_value(
		"Journal Entry",
		name,
		{"custom_is_reversed": 1 if live_counterpart else 0, "custom_reversed_by": live_counterpart},
		update_modified=False,
	)


def sync(doc, method=None):
	if doc.reversal_of:
		refresh(doc.reversal_of)
