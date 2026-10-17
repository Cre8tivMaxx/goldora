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
