from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from pure_life.asset_maintenance import (
	KM_PERIODICITY,
	km_task_is_due,
	update_maintenance_log_if_allowed,
	validate,
)
from pure_life.vehicle_log import on_submit

KM_CONDITION = "eval:doc.periodicity=='Kilometers'"


def make_task(**values):
	return frappe._dict({"idx": 1, "maintenance_task": "Oil change", "next_due_date": "2027-01-01", **values})


class TestKmPeriodicity(FrappeTestCase):
	def test_periodicity_offers_kilometers(self):
		options = frappe.get_meta("Asset Maintenance Task").get_field("periodicity").options.split("\n")
		self.assertIn(KM_PERIODICITY, options)

	def test_km_fields_show_and_are_required_only_for_kilometers(self):
		meta = frappe.get_meta("Asset Maintenance Task")
		interval = meta.get_field("custom_interval_km")
		self.assertEqual((interval.depends_on, interval.mandatory_depends_on), (KM_CONDITION, KM_CONDITION))
		self.assertEqual(meta.get_field("custom_last_service_odometer").depends_on, KM_CONDITION)

	def test_kilometers_task_without_interval_is_rejected(self):
		doc = SimpleNamespace(asset_maintenance_tasks=[make_task(periodicity=KM_PERIODICITY, custom_interval_km=0)])
		with self.assertRaisesRegex(frappe.ValidationError, "Interval \\(KM\\)"):
			validate(doc)

	def test_kilometers_task_has_no_date_based_due_date(self):
		task = make_task(periodicity=KM_PERIODICITY, custom_interval_km=5000)
		validate(SimpleNamespace(asset_maintenance_tasks=[task]))
		self.assertIsNone(task.next_due_date)

	def test_date_based_task_is_untouched(self):
		task = make_task(periodicity="Monthly", custom_interval_km=0)
		validate(SimpleNamespace(asset_maintenance_tasks=[task]))
		self.assertEqual(task.next_due_date, "2027-01-01")

	def test_km_due_check_uses_latest_submitted_vehicle_log(self):
		task = make_task(periodicity=KM_PERIODICITY, custom_interval_km=500, custom_last_service_odometer=1200)
		maintenance = frappe._dict(custom_vehicle="VEH-TEST")
		with (
			patch("pure_life.asset_maintenance.frappe.db.get_value", return_value=1500),
			patch("pure_life.asset_maintenance.frappe.get_all", return_value=[frappe._dict(odometer=1699)]),
		):
			self.assertFalse(km_task_is_due(maintenance, task))
		with (
			patch("pure_life.asset_maintenance.frappe.db.get_value", return_value=1500),
			patch("pure_life.asset_maintenance.frappe.get_all", return_value=[frappe._dict(odometer=1700)]),
		):
			self.assertTrue(km_task_is_due(maintenance, task))

	def test_km_log_creation_waits_until_due_but_updates_existing_log(self):
		task = make_task(name="TASK-1", periodicity=KM_PERIODICITY, custom_interval_km=500)
		maintenance = frappe._dict(name="AM-1", item_code="ITEM-1", item_name="Item", custom_vehicle="VEH-1")
		with (
			patch("pure_life.asset_maintenance.frappe.get_value", return_value=None),
			patch("pure_life.asset_maintenance.km_task_is_due", return_value=False),
			patch("pure_life.asset_maintenance.update_maintenance_log") as update,
		):
			update_maintenance_log_if_allowed(maintenance, task)
		update.assert_not_called()
		with (
			patch("pure_life.asset_maintenance.frappe.get_value", return_value="LOG-1"),
			patch("pure_life.asset_maintenance.update_maintenance_log") as update,
		):
			update_maintenance_log_if_allowed(maintenance, task)
		update.assert_called_once()

	def test_cancelled_task_does_not_recreate_log_during_parent_save(self):
		task = make_task(name="TASK-1", periodicity="Monthly")
		maintenance = frappe._dict(name="AM-1", item_code="ITEM-1", item_name="Item")
		with (
			patch("pure_life.asset_maintenance.frappe.get_value", return_value=None),
			patch("pure_life.asset_maintenance.update_maintenance_log") as update,
			patch.object(frappe.flags, "cancelled_maintenance_task", "TASK-1", create=True),
		):
			update_maintenance_log_if_allowed(maintenance, task)
		update.assert_not_called()

	def test_km_alert_skips_tasks_not_set_to_kilometers(self):
		task = frappe._dict(periodicity="Monthly", custom_interval_km=300, custom_last_service_odometer=0,
			custom_km_alert_sent_at=0, maintenance_task="Oil change", db_set=lambda *a, **k: None)
		maintenance = SimpleNamespace(asset_maintenance_tasks=[task])
		doc = SimpleNamespace(license_plate="VEH-TEST", odometer=5000, name="VLOG-TEST")
		with (
			patch.dict(frappe.conf, {"pure_life_fleet_features": True}),
			patch("pure_life.vehicle_log.frappe.get_all", return_value=["AM-TEST"]),
			patch("pure_life.vehicle_log.frappe.get_doc", return_value=maintenance),
			patch("pure_life.vehicle_log.send_alert") as send_alert,
		):
			on_submit(doc)
		send_alert.assert_not_called()
