import frappe
from frappe.tests.utils import FrappeTestCase

from pure_life.vehicle_log import get_last_fuel_price, validate


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

	def insert_vehicle(self, name, fuel_type):
		frappe.get_doc({"doctype": "Vehicle", "name": name, "license_plate": name, "fuel_type": fuel_type}).db_insert()

	def insert_log(self, vehicle, date, price, docstatus=1):
		doc = frappe.get_doc({"doctype": "Vehicle Log", "license_plate": vehicle, "date": date,
			"price": price, "docstatus": docstatus, "odometer": 1})
		doc.name = frappe.generate_hash(length=10)
		doc.db_insert()
		return doc

	def test_fuel_price_defaults_to_last_price_for_same_fuel_type(self):
		self.insert_vehicle("PL-DIESEL-1", "Diesel")
		self.insert_vehicle("PL-DIESEL-2", "Diesel")
		self.insert_vehicle("PL-PETROL-1", "Petrol")
		self.insert_log("PL-DIESEL-1", "2099-01-01", 15.5)
		self.insert_log("PL-DIESEL-2", "2099-02-01", 17.5)
		self.insert_log("PL-PETROL-1", "2099-03-01", 21)
		self.insert_log("PL-DIESEL-1", "2099-04-01", 99, docstatus=0)

		self.assertEqual(get_last_fuel_price("PL-DIESEL-1", "2099-05-01"), 17.5)
		self.assertEqual(get_last_fuel_price("PL-DIESEL-1", "2099-01-15"), 15.5)
		self.assertEqual(get_last_fuel_price("PL-PETROL-1", "2099-05-01"), 21)

		doc = self.make_vehicle_log(license_plate="PL-DIESEL-2", date="2099-05-01", fuel_qty=40)
		validate(doc)
		self.assertEqual(doc.price, 17.5)

		doc = self.make_vehicle_log(license_plate="PL-DIESEL-2", date="2099-05-01", fuel_qty=40, price=18)
		validate(doc)
		self.assertEqual(doc.price, 18)

	def test_totals_are_calculated(self):
		doc = self.make_vehicle_log(odometer=4594, last_odometer=4494, empty_weight=12000, loaded_weight=15500,
			empty_weight_doc_no="E-1", loaded_weight_doc_no="L-1", fuel_qty=40, price=19.25)
		validate(doc)
		self.assertEqual((doc.distance_km, doc.net_weight, doc.paid_amount), (100, 3500, 770))

	def test_disabled_vehicle_rejected(self):
		self.insert_vehicle("PL-DISABLED", "Diesel")
		frappe.db.set_value("Vehicle", "PL-DISABLED", "disabled", 1)
		doc = self.make_vehicle_log(license_plate="PL-DISABLED")
		with self.assertRaisesRegex(frappe.ValidationError, "Vehicle PL-DISABLED is disabled"):
			validate(doc)

	def test_dashboard_links_are_added_once(self):
		from pure_life.dashboard.delivery_trip import get_data as get_trip_dashboard
		from pure_life.dashboard.vehicle_log import get_data as get_log_dashboard

		trip_data = get_trip_dashboard({"fieldname": "custom_delivery_trip", "transactions": []})
		trip_data = get_trip_dashboard(trip_data)
		self.assertEqual(trip_data["internal_links"].get("Vehicle Log"), ["custom_delivery_trip"])
		self.assertEqual(sum("Vehicle Log" in x.get("items", []) for x in trip_data["transactions"]), 1)

		log_data = get_log_dashboard({"fieldname": "vehicle_log", "transactions": []})
		log_data = get_log_dashboard(log_data)
		self.assertEqual(log_data["internal_links"].get("Expense Claim"), ["vehicle_log"])
		self.assertEqual(sum("Expense Claim" in x.get("items", []) for x in log_data["transactions"]), 1)
