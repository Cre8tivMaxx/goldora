"""Vehicle Log weighbridge validations and fuel price defaults."""

import frappe
from frappe import _


def validate(doc, method=None):
	set_fuel_price(doc)
	if doc.empty_weight is not None and doc.loaded_weight is not None and doc.loaded_weight < doc.empty_weight:
		frappe.throw(_("Loaded weight cannot be less than empty weight."))

	for weight_field, document_field in (
		("empty_weight", "empty_weight_doc_no"),
		("loaded_weight", "loaded_weight_doc_no"),
	):
		if doc.get(weight_field) is not None and not doc.get(document_field):
			frappe.throw(_("Enter the document number for the {0}.").format(doc.meta.get_label(weight_field)))


def set_fuel_price(doc, method=None):
	if doc.fuel_qty and not doc.price:
		doc.price = get_last_fuel_price(doc.license_plate, doc.date, doc.name)


@frappe.whitelist()
def get_last_fuel_price(license_plate, date=None, exclude=None):
	"""Price of the latest submitted Vehicle Log for the same fuel type, like an item's last rate."""
	fuel_type = frappe.db.get_value("Vehicle", license_plate, "fuel_type") if license_plate else None
	if not fuel_type:
		return None

	log = frappe.qb.DocType("Vehicle Log")
	vehicle = frappe.qb.DocType("Vehicle")
	query = (
		frappe.qb.from_(log)
		.join(vehicle)
		.on(vehicle.name == log.license_plate)
		.select(log.price)
		.where((log.docstatus == 1) & (log.price > 0) & (vehicle.fuel_type == fuel_type))
		.orderby(log.date, order=frappe.qb.desc)
		.orderby(log.creation, order=frappe.qb.desc)
		.limit(1)
	)
	if date:
		query = query.where(log.date <= date)
	if exclude:
		query = query.where(log.name != exclude)

	result = query.run()
	return result[0][0] if result else None
