"""Kilometer-based periodicity for Asset Maintenance tasks."""

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.assets.doctype.asset_maintenance.asset_maintenance import AssetMaintenance as ERPNextAssetMaintenance
from erpnext.assets.doctype.asset_maintenance.asset_maintenance import update_maintenance_log
from erpnext.assets.doctype.asset_maintenance_log.asset_maintenance_log import AssetMaintenanceLog as ERPNextAssetMaintenanceLog

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


def km_task_is_due(asset_maintenance, task):
	"""Whether the linked vehicle has reached this task's kilometer interval."""
	interval = flt(task.get("custom_interval_km"))
	if interval <= 0 or not asset_maintenance.get("custom_vehicle"):
		return False
	last = flt(task.get("custom_last_service_odometer"))
	odometer = flt(frappe.db.get_value("Vehicle", asset_maintenance.custom_vehicle, "last_odometer"))
	latest = frappe.get_all(
		"Vehicle Log",
		filters={"license_plate": asset_maintenance.custom_vehicle, "docstatus": 1},
		fields=["odometer"],
		order_by="creation desc",
		limit=1,
	)
	if latest:
		odometer = flt(latest[0].odometer)
	return odometer - last >= interval


class AssetMaintenance(ERPNextAssetMaintenance):
	def sync_maintenance_tasks(self):
		tasks_names = []
		for task in self.get("asset_maintenance_tasks"):
			tasks_names.append(task.name)
			update_maintenance_log_if_allowed(self, task)
		logs = frappe.get_all(
			"Asset Maintenance Log",
			fields=["name"],
			filters={"asset_maintenance": self.name, "task": ("not in", tasks_names)},
		)
		for row in logs:
			frappe.get_doc("Asset Maintenance Log", row.name).db_set("maintenance_status", "Cancelled")


def update_maintenance_log_if_allowed(asset_maintenance, task):
	"""Keep existing open logs in sync; gate creation for km and just-cancelled tasks."""
	# A cancelled task stays cancelled even when later vehicle logs pass its interval.
	if task.get("maintenance_status") == "Cancelled":
		return
	open_log = frappe.get_value(
		"Asset Maintenance Log",
		{"asset_maintenance": asset_maintenance.name, "task": task.name,
		 "maintenance_status": ("in", ["Planned", "Overdue"])},
	)
	if open_log:
		update_maintenance_log(
			asset_maintenance=asset_maintenance.name,
			item_code=asset_maintenance.item_code,
			item_name=asset_maintenance.item_name,
			task=task,
		)
		return
	if getattr(frappe.flags, "cancelled_maintenance_task", None) == task.name:
		return
	if is_km_task(task) and not km_task_is_due(asset_maintenance, task):
		return
	update_maintenance_log(
		asset_maintenance=asset_maintenance.name,
		item_code=asset_maintenance.item_code,
		item_name=asset_maintenance.item_name,
		task=task,
	)


class AssetMaintenanceLog(ERPNextAssetMaintenanceLog):
	def on_submit(self):
		previous = getattr(frappe.flags, "cancelled_maintenance_task", None)
		if self.maintenance_status == "Cancelled":
			frappe.flags.cancelled_maintenance_task = self.task
		try:
			return super().on_submit()
		finally:
			frappe.flags.cancelled_maintenance_task = previous
