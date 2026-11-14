from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from pure_life.delivery_trip import before_update_after_submit
from pure_life.vehicle_log import on_submit


class TestFeatureHooks(FrappeTestCase):
	def test_completing_trip_requires_submitted_vehicle_log(self):
		previous = SimpleNamespace(status="In Transit")
		doc = SimpleNamespace(name="DT-TEST", status="In Transit", delivery_stops=[SimpleNamespace(visited=1)],
			get_doc_before_save=lambda: previous)
		with patch("pure_life.delivery_trip.frappe.db.exists", return_value=False):
			with self.assertRaisesRegex(frappe.ValidationError, "Please create and submit the Vehicle Log"):
				before_update_after_submit(doc)

	def test_km_hook_ignores_when_flag_disabled(self):
		doc = SimpleNamespace(license_plate="VEH-TEST", odometer=12345)
		with patch.dict(frappe.conf, {"pure_life_fleet_features": False}), patch("pure_life.vehicle_log.frappe.get_all") as get_all:
			on_submit(doc)
		get_all.assert_not_called()

	def test_km_hook_checks_non_submittable_asset_maintenance(self):
		task = frappe._dict(
			periodicity="Kilometers",
			custom_interval_km=300,
			custom_last_service_odometer=4000,
			custom_km_alert_sent_at=0,
			maintenance_task="Oil change",
			assign_to="fleet.user@example.com",
			db_set=lambda *args, **kwargs: None,
		)
		maintenance = SimpleNamespace(asset_maintenance_tasks=[task])
		doc = SimpleNamespace(license_plate="VEH-TEST", odometer=4501, name="VLOG-TEST")
		created = []

		def make_doc(values):
			created.append(values)
			return SimpleNamespace(insert=lambda **kwargs: None)

		def get_doc(*args):
			return maintenance if args[-1] == "AM-TEST" else make_doc(args[0])

		with (
			patch.dict(frappe.conf, {"pure_life_fleet_features": True}),
			patch("pure_life.vehicle_log.frappe.get_all", side_effect=[["AM-TEST"]]) as get_all,
			patch("pure_life.vehicle_log.fleet_alert_recipients", return_value=[]),
			patch("pure_life.vehicle_log.frappe.get_doc", side_effect=get_doc),
			patch("pure_life.vehicle_log.frappe.sendmail"),
			patch("pure_life.vehicle_log.frappe.db.get_value", return_value=None),
		):
			on_submit(doc)

		self.assertEqual(get_all.call_args_list[0].kwargs["filters"], {"custom_vehicle": "VEH-TEST"})
		self.assertEqual(len(created), 1)
		self.assertIn("has exceeded 501 km", created[0]["subject"])
