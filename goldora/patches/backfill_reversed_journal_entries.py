"""Backfill custom_is_reversed / custom_reversed_by for Journal Entries reversed
before goldora.reversal.sync existed.

Run from hooks.py's after_migrate (not patches.txt): a post_model_sync patch
runs before sync_fixtures and is marked done in the Patch Log even if it
no-ops (this silently never ran on Frappe Cloud), with no way to retry it.
This function is idempotent, so after_migrate re-runs it on every migrate.
"""

import frappe
from frappe.utils.fixtures import sync_fixtures

from goldora.reversal import refresh


def execute():
	sync_fixtures("goldora")

	# Idempotent reset, then rebuild from what's actually live. Scoped to rows that
	# carry a flag: this runs on every migrate, and an unfiltered UPDATE rewrites the
	# whole Journal Entry table each deploy.
	frappe.db.sql(
		"""UPDATE `tabJournal Entry` SET custom_is_reversed = 0, custom_reversed_by = NULL
		WHERE custom_is_reversed = 1 OR custom_reversed_by IS NOT NULL"""
	)

	names = {
		*frappe.get_all(
			"Journal Entry",
			filters={"docstatus": 1, "reversal_of": ("is", "set")},
			pluck="reversal_of",
		),
		*frappe.get_all(
			"Journal Entry",
			filters={"docstatus": ("<", 2), "inter_company_journal_entry_reference": ("is", "set")},
			pluck="inter_company_journal_entry_reference",
		),
	}

	# ponytail: one refresh per name, fine at current JE volume; batch SQL if it grows.
	for name in names:
		refresh(name)

	print(f"I: {len(names)} original Journal Entries flagged")
