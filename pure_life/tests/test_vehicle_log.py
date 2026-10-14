import frappe
from frappe.tests.utils import FrappeTestCase

from pure_life.vehicle_log import validate


class TestVehicleLog(FrappeTestCase):
	def make_vehicle_log(self, **values):
		return frappe.get_doc({"doctype": "Vehicle Log", "license_plate": "TEST", **values})

	def test_loaded_weight_cannot_be_less_than_empty_weight(self):
		doc = self.make_vehicle_log(empty_weight=12000, loaded_weight=11000,
			empty_weight_doc_no="EMPTY-1", loaded_weight_doc_no="LOADED-1")
		with self.assertRaisesRegex(frappe.ValidationError, "Loaded weight cannot be less than empty weight"):
			validate(doc)

	def test_weight_requires_document_number(self):
		for weight_field, values in (
			("empty_weight", {"empty_weight": 12000}),
			("loaded_weight", {"loaded_weight": 15000}),
		):
			with self.subTest(weight_field=weight_field):
				doc = self.make_vehicle_log(**values)
				label = doc.meta.get_label(weight_field)
				with self.assertRaises(frappe.ValidationError) as error:
					validate(doc)
				self.assertEqual(str(error.exception), f"Enter the document number for the {label}.")
