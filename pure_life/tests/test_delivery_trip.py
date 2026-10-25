import frappe
from unittest.mock import patch
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, now_datetime, nowdate

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from pure_life.delivery_trip import (
	RULES,
	before_submit,
	make_delivery_trip_from_purchase_receipt,
	make_delivery_trip_from_stock_entry,
)
from pure_life.waste_chain import make_purchase_receipt_from_delivery_note, make_stock_entry_from_purchase_receipt
from pure_life.vehicle_log import TRIP_DOCUMENT_RECIPIENTS, notify_other_movements


class TestDeliveryTrip(FrappeTestCase):
	def test_documents_gate_requires_attached_documents(self):
		doc = frappe._dict(name="TRIP-1", delivery_stops=[])
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}), \
			patch("pure_life.delivery_trip.frappe.db.get_value", side_effect=["VLOG-1", 0]):
			with self.assertRaisesRegex(frappe.ValidationError, "Documents Attached"):
				before_submit(doc)
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}), \
			patch("pure_life.delivery_trip.frappe.db.get_value", side_effect=["VLOG-1", 1]):
			before_submit(doc)

	def test_documents_notification_roles_follow_trip_type(self):
		self.assertEqual(TRIP_DOCUMENT_RECIPIENTS["Selling"], ("Sales Manager", "Delivery Note", "delivery_note"))
		self.assertEqual(TRIP_DOCUMENT_RECIPIENTS["Buying"], ("Purchase Manager", "Purchase Receipt", "purchase_receipt"))
		self.assertEqual(TRIP_DOCUMENT_RECIPIENTS["Warehouse Transfer"], ("Stock Manager", "Stock Entry", "stock_entry"))
	def test_selling_requires_delivery_note(self):
		self.assertIn("delivery_note", RULES["Selling"][0])
		self.assertNotIn("delivery_note", RULES["Selling"][1])

	def setUp(self):
		super().setUp()
		self.fleet_flag = patch.dict(frappe.conf, {"pure_life_fleet_features": False})
		self.fleet_flag.start()
		self.addCleanup(self.fleet_flag.stop)
		self.prefix = "PL Trip " + frappe.generate_hash(length=8)
		self.company = frappe.get_doc({
			"doctype": "Company", "company_name": self.prefix,
			"abbr": frappe.generate_hash(length=5).upper(), "default_currency": "USD",
			"country": "United States", "create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
		}).insert()
		year = getdate(nowdate()).year
		frappe.get_doc({"doctype": "Fiscal Year", "year": self.prefix,
			"year_start_date": f"{year}-01-01", "year_end_date": f"{year}-12-31",
			"companies": [{"company": self.company.name}]}).insert()
		self.project = frappe.get_doc({"doctype": "Project", "project_name": self.prefix,
			"company": self.company.name}).insert()
		self.supplier = frappe.get_doc({"doctype": "Supplier", "supplier_name": self.prefix + " Supplier",
			"supplier_group": "All Supplier Groups", "supplier_type": "Company"}).insert()
		self.customer_group = frappe.get_doc({"doctype": "Customer Group",
			"customer_group_name": self.prefix, "parent_customer_group": "All Customer Groups", "is_group": 0}).insert()
		self.territory = frappe.get_doc({"doctype": "Territory", "territory_name": self.prefix,
			"parent_territory": "All Territories", "is_group": 0}).insert()
		self.customer = frappe.get_doc({"doctype": "Customer", "customer_name": self.prefix + " Customer",
			"customer_group": self.customer_group.name, "territory": self.territory.name,
			"customer_type": "Company"}).insert()
		self.address = frappe.get_doc({"doctype": "Address", "address_title": self.prefix,
			"address_line1": "1 Test Street", "city": "Test City", "country": "United States",
			"links": [{"link_doctype": "Supplier", "link_name": self.supplier.name}],
			"is_primary_address": 1}).insert()
		self.driver = frappe.get_doc({"doctype": "Driver", "full_name": self.prefix,
			"license_number": self.prefix}).insert()
		self.vehicle = frappe.get_doc({"doctype": "Vehicle", "license_plate": self.prefix,
			"make": "Test", "model": "Test", "last_odometer": 0,
			"acquisition_date": nowdate(), "location": "Test", "chassis_no": self.prefix,
			"uom": "Litre", "vehicle_value": 1000}).insert()
		self.item = frappe.get_doc({"doctype": "Item", "item_code": self.prefix,
			"item_name": self.prefix, "item_group": "All Item Groups", "stock_uom": "Nos",
			"is_stock_item": 1}).insert()
		self.warehouses = [frappe.get_doc({"doctype": "Warehouse", "warehouse_name": f"{self.prefix} {i}",
			"company": self.company.name}).insert().name for i in (1, 2)]

	def receipt(self, submit=True):
		doc = frappe.get_doc({"doctype": "Purchase Receipt", "company": self.company.name,
			"supplier": self.supplier.name, "supplier_address": self.address.name, "project": self.project.name,
			"currency": "USD", "conversion_rate": 1, "posting_date": nowdate(),
			"items": [{"item_code": self.item.name, "qty": 10, "rate": 10,
				"warehouse": self.warehouses[0]}]}).insert()
		if submit:
			doc.submit()
		return doc

	def transfer(self, submit=True):
		doc = make_stock_entry(company=self.company.name, item_code=self.item.name, qty=1, rate=10,
			from_warehouse=self.warehouses[0], to_warehouse=self.warehouses[1], do_not_save=True)
		doc.project = self.project.name
		doc.from_warehouse, doc.to_warehouse = self.warehouses
		doc.insert()
		if submit:
			doc.submit()
		return doc

	def trip(self, trip_type, **row):
		return frappe.get_doc({"doctype": "Delivery Trip", "trip_type": trip_type,
			"company": self.company.name, "driver": self.driver.name,
			"driver_name": self.driver.full_name, "vehicle": self.vehicle.name,
			"departure_time": now_datetime(), "delivery_stops": [row]}).insert()

	def assert_transport(self, doc, trip=None):
		doc.reload()
		for field, value in {"driver": self.driver.name, "driver_name": self.driver.full_name,
			"vehicle_no": self.vehicle.name, "delivery_trip": trip.name if trip else None}.items():
			if trip:
				self.assertEqual(doc.get(field), value)
			else:
				self.assertFalse(doc.get(field))

	def test_buying_submitted_receipt_save_and_cancel(self):
		pr = self.receipt()
		trip = self.trip("Buying", supplier=self.supplier.name, address=self.address.name, purchase_receipt=pr.name)
		self.assert_transport(pr, trip)
		self.assertEqual(pr.lr_no, self.vehicle.name)
		self.assertEqual(getdate(pr.lr_date), getdate(trip.departure_time))
		trip.submit()
		trip.cancel()
		self.assert_transport(pr)
		self.assertFalse(pr.lr_no)
		self.assertFalse(pr.lr_date)

	def test_transfer_without_address(self):
		self.receipt()
		se = self.transfer()
		trip = self.trip("Warehouse Transfer", stock_entry=se.name)
		self.assertFalse(trip.delivery_stops[0].address)
		self.assertEqual(trip.delivery_stops[0].customer_address, " → ".join(self.warehouses))
		self.assert_transport(se, trip)
		trip.submit()
		trip.cancel()
		self.assert_transport(se)

	def test_transfer_warehouses_fall_back_to_distinct_item_warehouses(self):
		self.receipt()
		se = self.transfer(submit=False)
		se.from_warehouse = None
		se.to_warehouse = None
		se.append("items", {"item_code": self.item.name, "qty": 1, "s_warehouse": self.warehouses[0],
			"t_warehouse": self.warehouses[1], "project": self.project.name})
		se.save()
		trip = self.trip("Warehouse Transfer", stock_entry=se.name)
		stop = trip.delivery_stops[0]
		self.assertEqual(stop.source_warehouse, self.warehouses[0])
		self.assertEqual(stop.target_warehouse, self.warehouses[1])
		self.assertEqual(stop.customer_address, " → ".join(self.warehouses))
		self.assertNotIn("None", stop.customer_address)

	def test_duplicate_source_rejected(self):
		pr = self.receipt(submit=False)
		with self.assertRaisesRegex(frappe.ValidationError, "Row 2:.*already in row 1"):
			frappe.get_doc({"doctype": "Delivery Trip", "trip_type": "Buying", "company": self.company.name,
				"delivery_stops": [
					{"supplier": self.supplier.name, "address": self.address.name, "purchase_receipt": pr.name},
					{"supplier": self.supplier.name, "address": self.address.name, "purchase_receipt": pr.name},
				]}).insert()

	def test_draft_receipt_blocks_submit(self):
		pr = self.receipt(submit=False)
		trip = self.trip("Buying", supplier=self.supplier.name, address=self.address.name, purchase_receipt=pr.name)
		with self.assertRaisesRegex(frappe.ValidationError, "draft state"):
			trip.submit()

	def test_selling_delivery_note_regression(self):
		self.receipt()
		dn = frappe.get_doc({"doctype": "Delivery Note", "company": self.company.name,
			"customer": self.customer.name, "project": self.project.name, "currency": "USD", "conversion_rate": 1,
			"items": [{"item_code": self.item.name, "qty": 1, "rate": 20,
				"warehouse": self.warehouses[0]}]}).insert().submit()
		trip = self.trip("Selling", customer=self.customer.name, address=self.address.name, delivery_note=dn.name)
		self.assert_transport(dn, trip)
		from erpnext.stock.doctype.delivery_note.delivery_note import make_delivery_trip
		self.assertEqual(make_delivery_trip(dn.name).trip_type, "Selling")

	def test_waste_chain_creates_purchase_receipt_and_stock_entry(self):
		service_item = frappe.get_doc({"doctype": "Item", "item_code": self.prefix + " Service",
			"item_name": self.prefix + " Service", "item_group": "All Item Groups", "stock_uom": "Nos",
			"is_stock_item": 0, "is_purchase_item": 1}).insert()
		dn = frappe.get_doc({"doctype": "Delivery Note", "company": self.company.name,
			"customer": self.customer.name, "project": self.project.name, "currency": "USD", "conversion_rate": 1,
			"items": [{"item_code": service_item.name, "qty": 2, "rate": 20}]}).insert().submit()
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}):
			result = make_purchase_receipt_from_delivery_note(dn.name, self.supplier.name)
		pr = frappe.get_doc("Purchase Receipt", result["name"])
		self.assertEqual(pr.custom_delivery_note, dn.name)
		self.assertEqual(pr.custom_auto_created, 1)
		self.assertEqual(pr.project, self.project.name)
		pr.delete()
		stock_pr = self.receipt()
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}):
			se_result = make_stock_entry_from_purchase_receipt(stock_pr.name, self.warehouses[1])
		se = frappe.get_doc("Stock Entry", se_result["name"])
		self.assertEqual(se.purpose, "Material Receipt")
		self.assertEqual(se.custom_purchase_receipt, stock_pr.name)
		self.assertEqual(se.items[0].t_warehouse, self.warehouses[1])

	def test_stock_entry_from_service_purchase_receipt_returns_new_form_payload(self):
		service_item = frappe.get_doc({"doctype": "Item", "item_code": self.prefix + " Burial",
			"item_name": self.prefix + " Burial", "item_group": "All Item Groups", "stock_uom": "Nos",
			"is_stock_item": 0, "is_purchase_item": 1}).insert()
		pr = frappe.get_doc({"doctype": "Purchase Receipt", "company": self.company.name,
			"supplier": self.supplier.name, "supplier_address": self.address.name, "project": self.project.name,
			"currency": "USD", "conversion_rate": 1, "posting_date": nowdate(),
			"items": [{"item_code": service_item.name, "qty": 1, "rate": 10}]}).insert().submit()
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}):
			payload = make_stock_entry_from_purchase_receipt(pr.name, self.warehouses[1])
		self.assertIn("new", payload)
		self.assertEqual(payload["new"]["purpose"], "Material Receipt")
		self.assertEqual(payload["new"]["to_warehouse"], self.warehouses[1])
		self.assertEqual(payload["new"]["custom_purchase_receipt"], pr.name)

	def test_waste_chain_methods_are_gated(self):
		with patch.dict(frappe.conf, {"pure_life_fleet_features": False}):
			with self.assertRaisesRegex(frappe.ValidationError, "Fleet features are disabled"):
				make_purchase_receipt_from_delivery_note("missing", "missing")

	def test_wrong_party_rejected(self):
		with self.assertRaisesRegex(frappe.ValidationError, "must be empty"):
			self.trip("Buying", supplier=self.supplier.name, customer=self.customer.name, address=self.address.name)

	def test_disabled_vehicle_rejected(self):
		frappe.db.set_value("Vehicle", self.vehicle.name, "disabled", 1)
		with self.assertRaisesRegex(frappe.ValidationError, f"Vehicle {self.vehicle.name} is disabled"):
			self.trip("Buying", supplier=self.supplier.name, address=self.address.name)

	def test_removed_receipt_and_delete_clear_transport(self):
		pr = self.receipt(submit=False)
		trip = self.trip("Buying", supplier=self.supplier.name, address=self.address.name, purchase_receipt=pr.name)
		trip.set("delivery_stops", [{"supplier": self.supplier.name, "address": self.address.name}])
		trip.save()
		self.assert_transport(pr)
		trip.append("delivery_stops", {"supplier": self.supplier.name, "address": self.address.name,
			"purchase_receipt": pr.name})
		trip.save()
		trip.delete()
		self.assert_transport(pr)

	def test_mappers(self):
		pr = self.receipt()
		trip = make_delivery_trip_from_purchase_receipt(pr.name)
		self.assertEqual(trip.trip_type, "Buying")
		self.assertEqual(trip.company, self.company.name)
		self.assertEqual(trip.delivery_stops[0].supplier, self.supplier.name)
		self.assertEqual(trip.delivery_stops[0].address, self.address.name)
		se = self.transfer(submit=False)
		mapped = make_delivery_trip_from_stock_entry(se.name)
		self.assertEqual(mapped.trip_type, "Warehouse Transfer")
		self.assertEqual(mapped.delivery_stops[0].stock_entry, se.name)
		with self.assertRaises(frappe.ValidationError):
			make_delivery_trip_from_stock_entry(se.name, trip)

	def other_trip(self, *stops):
		return frappe.get_doc({"doctype": "Delivery Trip", "trip_type": "Other Movements",
			"company": self.company.name, "driver": self.driver.name,
			"driver_name": self.driver.full_name, "vehicle": self.vehicle.name,
			"departure_time": now_datetime(), "delivery_stops": list(stops)})

	def test_other_movements_saves_without_documents_customer_or_address(self):
		trip = self.other_trip({"custom_movement_description": "Vehicle inspection"}).insert()
		stop = trip.delivery_stops[0]
		self.assertFalse(stop.address or stop.customer or stop.customer_address)
		trip.reload()
		self.assertEqual(trip.delivery_stops[0].custom_movement_description, "Vehicle inspection")

	def test_other_movements_stop_description_required(self):
		for stop in ({}, {"custom_movement_description": "  "}):
			with self.assertRaisesRegex(frappe.ValidationError, "Row 1: Movement Description is required"):
				self.other_trip(stop).insert()
		with self.assertRaisesRegex(frappe.ValidationError, "Row 2: Movement Description is required"):
			self.other_trip({"custom_movement_description": "Exit"}, {}).insert()

	def test_other_movements_rejects_documents(self):
		self.receipt()
		se = self.transfer(submit=False)
		with self.assertRaisesRegex(frappe.ValidationError, "must be empty"):
			self.other_trip({"custom_movement_description": "Exit", "stock_entry": se.name}).insert()

	def test_other_movements_submit_needs_vehicle_log_but_not_documents(self):
		trip = self.other_trip({"custom_movement_description": "Exit"}).insert()
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}):
			with self.assertRaisesRegex(frappe.ValidationError, "create the Vehicle Log"):
				trip.submit()
			log = frappe.get_doc({"doctype": "Vehicle Log", "license_plate": self.vehicle.name,
				"custom_delivery_trip": trip.name, "date": nowdate(), "odometer": 10,
				"custom_documents_attached": 0}).insert()
			trip.reload()
			trip.submit()
			self.assertEqual(trip.docstatus, 1)

	def test_other_movements_vehicle_log_notifies_fleet_managers_only(self):
		email = frappe.generate_hash(length=8) + "@example.com"
		manager = frappe.get_doc({"doctype": "User", "email": email, "first_name": "Fleet",
			"send_welcome_email": 0, "roles": [{"role": "Fleet Manager"}]}).insert()
		trip = self.other_trip({"custom_movement_description": "Inspection"}).insert()
		log = frappe.get_doc({"doctype": "Vehicle Log", "license_plate": self.vehicle.name,
			"custom_delivery_trip": trip.name, "date": nowdate(), "odometer": 10}).insert()
		filters = {"for_user": manager.name, "document_type": "Vehicle Log", "document_name": log.name}
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}):
			log.custom_documents_attached = 1
			log.save()
			self.assertFalse(frappe.db.exists("Notification Log", filters))
			notify_other_movements(log)
		self.assertEqual(frappe.db.count("Notification Log", filters), 1)
		# Trips of other types do not notify on submit.
		buying = self.trip("Buying", supplier=self.supplier.name, address=self.address.name)
		other_log = frappe.get_doc({"doctype": "Vehicle Log", "license_plate": self.vehicle.name,
			"custom_delivery_trip": buying.name, "date": nowdate(), "odometer": 20}).insert()
		with patch.dict(frappe.conf, {"pure_life_fleet_features": True}):
			notify_other_movements(other_log)
		self.assertFalse(frappe.db.exists("Notification Log", {**filters, "document_name": other_log.name}))
