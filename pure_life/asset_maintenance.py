"""Kilometer-based periodicity for Asset Maintenance tasks."""

import frappe
from frappe import _
from frappe.utils import flt

# Extra Periodicity option (added by a Property Setter fixture) for tasks driven by odometer, not dates.
KM_PERIODICITY = "Kilometers"


def is_km_task(task):
	return task.get("periodicity") == KM_PERIODICITY


def validate(doc, method=None):
	for task in doc.asset_maintenance_tasks:
		if not is_km_task(task):
			continue
		if flt(task.get("custom_interval_km")) <= 0:
			frappe.throw(_("Row #{0}: Interval (KM) is required for {1} when Periodicity is Kilometers.").format(
				task.idx, task.maintenance_task))
		# Due by distance, so ERPNext's date-based due date does not apply.
		task.next_due_date = None
