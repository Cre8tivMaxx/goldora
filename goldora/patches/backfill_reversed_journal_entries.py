"""Backfill custom_is_reversed / custom_reversed_by for Journal Entries reversed
before goldora.reversal.sync existed.

Post-model-sync patches run before sync_fixtures (frappe/migrate.py), so the
custom fields this patch writes to may not exist yet -- sync them first.
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
