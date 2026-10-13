"""Delivery Trip support for incoming goods and warehouse transfers."""

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_link_to_form, getdate

SOURCES = {"purchase_receipt": "Purchase Receipt", "stock_entry": "Stock Entry"}
RULES = {
	"Selling": (("customer", "address"), ("supplier", "purchase_receipt", "stock_entry")),
	"Buying": (("supplier", "address"), ("customer", "delivery_note", "stock_entry")),
	"Warehouse Transfer": (("stock_entry",), ("customer", "supplier", "delivery_note", "purchase_receipt")),
}


def before_validate(doc, method=None):
	# The core controller resolves addresses before the validate doc event.
	validate(doc)
	for stop in doc.delivery_stops:
		if doc.trip_type == "Warehouse Transfer":
			warehouses = frappe.db.get_value(
				"Stock Entry", stop.stock_entry, ["from_warehouse", "to_warehouse"], as_dict=True
			)
			stop.source_warehouse = warehouses.from_warehouse
			stop.target_warehouse = warehouses.to_warehouse
			stop.customer_address = f"{stop.source_warehouse or ''} → {stop.target_warehouse or ''}"
		else:
			stop.customer_address = get_address_display(frappe.get_doc("Address", stop.address).as_dict())


def validate(doc, method=None):
	if doc.trip_type not in RULES:
		frappe.throw(_("Please select a Trip Type."))
	previous = doc.get_doc_before_save()
	if previous and previous.trip_type and previous.delivery_stops and previous.trip_type != doc.trip_type:
		frappe.throw(_("Trip Type cannot change once the trip has stops."))
	required, forbidden = RULES[doc.trip_type]
	for stop in doc.delivery_stops:
		for field in required:
			if not stop.get(field):
				frappe.throw(_("Row {0}: {1} is required for {2}.").format(
					stop.idx, stop.meta.get_label(field), doc.trip_type
				))
		for field in forbidden:
			if stop.get(field):
				frappe.throw(_("Row {0}: {1} must be empty for {2}.").format(
					stop.idx, stop.meta.get_label(field), doc.trip_type
				))
		if stop.stock_entry:
			if frappe.db.get_value("Stock Entry", stop.stock_entry, "stock_entry_type") != "Material Transfer":
				frappe.throw(_("Row {0}: Stock Entry must be a Material Transfer.").format(stop.idx))
		for field, doctype in SOURCES.items():
			if stop.get(field):
				source = frappe.db.get_value(doctype, stop.get(field), ["company", "docstatus"], as_dict=True)
				if not source or source.company != doc.company or source.docstatus == 2:
					frappe.throw(_("Row {0}: {1} must belong to this company and must not be cancelled.").format(stop.idx, doctype))


def before_submit(doc, method=None):
	for field, doctype in SOURCES.items():
		names = {stop.get(field) for stop in doc.delivery_stops if stop.get(field)}
		if not names:
			continue
		drafts = frappe.get_all(doctype, filters={"name": ["in", list(names)], "docstatus": 0}, pluck="name")
		if drafts:
			frappe.throw(_("{0} should not be in draft state when submitting a Delivery Trip: {1}. Please submit them first.").format(doctype, ", ".join(drafts)))


def sync_transport(doc, method=None):
	clear = method in ("on_cancel", "on_trash", "on_discard")
	for field, doctype in SOURCES.items():
		current = {stop.get(field) for stop in doc.delivery_stops if stop.get(field)}
		linked = set(frappe.get_all(doctype, filters={"delivery_trip": doc.name}, pluck="name"))
		updated = []
		for name in sorted(current | linked):
			source = frappe.get_doc(doctype, name)
			remove = clear or name not in current
			# A removed row must not clear a document subsequently assigned to another trip.
			if remove and source.delivery_trip != doc.name:
				continue
			values = {"driver": doc.driver, "driver_name": doc.driver_name,
				"vehicle_no": doc.vehicle, "delivery_trip": doc.name}
			if doctype == "Purchase Receipt":
				values.update(lr_no=doc.name, lr_date=doc.departure_time)
			changed = False
			for key, value in values.items():
				value = None if remove else value
				# Dates read back as date objects; compare their serialized date part.
				if key == "lr_date" and value:
					value = getdate(value)
				if source.get(key) != value:
					source.set(key, value)
					changed = True
			if changed:
				source.flags.ignore_validate_update_after_submit = True
				source.save()
				updated.append(get_link_to_form(doctype, name))
		if updated:
			frappe.msgprint(_("{0} {1} updated").format(doctype, ", ".join(updated)))


def _map_source(doctype, source_name, trip_type, field, target_doc):
	if isinstance(target_doc, str):
		target_doc = frappe.get_doc(frappe.parse_json(target_doc))
	if not target_doc:
		target_doc = frappe.new_doc("Delivery Trip")
		# A Create action must inherit the source company rather than user defaults.
		target_doc.company = None
	if target_doc.docstatus != 0:
		frappe.throw(_("Stops can only be added to a Draft trip."))
	if target_doc.trip_type and target_doc.trip_type != trip_type:
		frappe.throw(_("The source document does not match this Trip Type."))

	def set_stop(source, stop, parent):
		if source.docstatus == 2:
			frappe.throw(_("Cancelled documents cannot be added to a Delivery Trip."))
		if target_doc.company and target_doc.company != source.company:
			frappe.throw(_("The source document must belong to the trip company."))
		target_doc.company = source.company
		if doctype == "Purchase Receipt":
			stop.address = source.supplier_address
			stop.customer_address = source.address_display
		else:
			if source.stock_entry_type != "Material Transfer":
				frappe.throw(_("Stock Entry must be a Material Transfer."))
			stop.source_warehouse = source.from_warehouse
			stop.target_warehouse = source.to_warehouse
			stop.customer_address = f"{source.from_warehouse or ''} → {source.to_warehouse or ''}"

	target_doc.trip_type = trip_type
	return get_mapped_doc(doctype, source_name, {doctype: {
		"doctype": "Delivery Stop", "on_parent": target_doc,
		"field_map": {"name": field, "contact_person": "contact", "contact_display": "customer_contact"},
		"postprocess": set_stop,
	}}, ignore_child_tables=True)


@frappe.whitelist()
def make_delivery_trip_from_purchase_receipt(source_name, target_doc=None):
	return _map_source("Purchase Receipt", source_name, "Buying", "purchase_receipt", target_doc)


@frappe.whitelist()
def make_delivery_trip_from_stock_entry(source_name, target_doc=None):
	return _map_source("Stock Entry", source_name, "Warehouse Transfer", "stock_entry", target_doc)


@frappe.whitelist()
def get_supplier_contact_and_address(supplier):
	frappe.has_permission("Supplier", "read", doc=supplier, throw=True)
	from frappe.contacts.doctype.contact.contact import get_default_contact
	from frappe.contacts.doctype.address.address import get_default_address

	return {"address": get_default_address("Supplier", supplier),
		"contact": get_default_contact("Supplier", supplier)}


def after_mapping(doc, method=None, source=None, table_maps=None):
	# Preserve the standard Delivery Note Create action without a field default.
	if source and source.doctype == "Delivery Note":
		if doc.trip_type and doc.trip_type != "Selling":
			frappe.throw(_("Delivery Notes can only be added to Selling trips."))
		doc.trip_type = "Selling"
