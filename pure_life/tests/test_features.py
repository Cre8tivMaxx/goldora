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

	def test_service_rows_update_last_service_odometer(self):
		doc = SimpleNamespace(license_plate="VEH-TEST", odometer=12345, service_detail=[{}], get=lambda k: [{}])
		with patch("pure_life.vehicle_log.frappe.db.set_value") as set_value:
			on_submit(doc)
		set_value.assert_called_once_with("Vehicle", "VEH-TEST", "custom_last_service_odometer", 12345.0)

	def test_due_vehicle_service_creates_fleet_notification(self):
		doc = SimpleNamespace(license_plate="VEH-TEST", odometer=12500, service_detail=[], name="LOG-TEST",
			get=lambda k: [])
		with patch("pure_life.vehicle_log.frappe.db.get_value", return_value={
			"custom_service_interval_km": 1000, "custom_last_service_odometer": 11000
		}), patch("pure_life.vehicle_log.frappe.get_all", return_value=["fleet@example.com"]), \
			patch("pure_life.vehicle_log.frappe.get_doc") as get_doc, \
			patch("pure_life.vehicle_log.frappe.sendmail") as sendmail:
			on_submit(doc)
		self.assertEqual(get_doc.call_args.args[0]["doctype"], "Notification Log")
		self.assertIn("1500 km", get_doc.call_args.args[0]["subject"])
		sendmail.assert_called_once()
