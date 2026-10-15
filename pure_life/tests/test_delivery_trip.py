import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, now_datetime, nowdate

from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from pure_life.delivery_trip import (
	make_delivery_trip_from_purchase_receipt,
	make_delivery_trip_from_stock_entry,
)


class TestDeliveryTrip(FrappeTestCase):
	def setUp(self):
		super().setUp()
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
