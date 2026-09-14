"""Keep the original Journal Entry's reversed-flag in step with its reversal.

erpnext.accounts.doctype.journal_entry.journal_entry.make_reverse_journal_entry
writes `reversal_of` only on the *reversing* entry; the original never learns it
has been reversed. This mirrors that link back onto the original so it can be
listed/filtered on (custom_is_reversed) and jumped to (custom_reversed_by).
"""

import frappe


def sync(doc, method=None):
	if not doc.reversal_of:
		return

	# read the DB, not `doc`: on_submit/on_cancel both run after the docstatus
	# change is already committed, so this single query covers both directions,
	# including a second reversal replacing a cancelled one.
	live_reversal = frappe.db.get_value(
		"Journal Entry", {"reversal_of": doc.reversal_of, "docstatus": 1}, "name"
	)

	frappe.db.set_value(
		"Journal Entry",
		doc.reversal_of,
		{"custom_is_reversed": 1 if live_reversal else 0, "custom_reversed_by": live_reversal},
		update_modified=False,
	)
