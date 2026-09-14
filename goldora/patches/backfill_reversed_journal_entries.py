"""Backfill custom_is_reversed / custom_reversed_by for Journal Entries reversed
before goldora.reversal.sync existed.

Run from hooks.py's after_migrate (not patches.txt): a post_model_sync patch
runs before sync_fixtures and is marked done in the Patch Log even if it
no-ops (this silently never ran on Frappe Cloud), with no way to retry it.
This function is idempotent, so after_migrate re-runs it on every migrate.
"""

import frappe
from frappe.utils.fixtures import sync_fixtures


def execute():
	sync_fixtures("goldora")

	# idempotent reset, then rebuild from what's actually live
	frappe.db.sql(
		"UPDATE `tabJournal Entry` SET custom_is_reversed = 0, custom_reversed_by = NULL"
	)

	pairs = frappe.db.sql(
		"""
		SELECT reversal_of, name
		FROM `tabJournal Entry`
		WHERE docstatus = 1 AND reversal_of IS NOT NULL AND reversal_of != ''
		""",
		as_dict=True,
	)

	for pair in pairs:
		frappe.db.set_value(
			"Journal Entry",
			pair.reversal_of,
			{"custom_is_reversed": 1, "custom_reversed_by": pair.name},
			update_modified=False,
		)

	print(f"backfill_reversed_journal_entries: {len(pairs)} original Journal Entries flagged")
