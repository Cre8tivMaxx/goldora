import frappe
from frappe import _
from frappe.utils import get_link_to_form, nowdate


def _require_enabled():
	if not frappe.conf.get("pure_life_fleet_features"):
		frappe.throw(_("Fleet features are disabled on this site."))


def _trip_for_delivery_note(delivery_note):
	return frappe.db.get_value("Delivery Stop", {"delivery_note": delivery_note}, "parent")


@frappe.whitelist()
def make_purchase_receipt_from_delivery_note(delivery_note, supplier, project=None):
	_require_enabled()
	dn = frappe.get_doc("Delivery Note", delivery_note)
	if dn.docstatus != 1:
		frappe.throw(_("Delivery Note must be submitted."))
	if frappe.db.exists("Purchase Receipt", {"custom_delivery_note": dn.name, "docstatus": ["<", 2]}):
		frappe.throw(_("A Purchase Receipt already exists for this Delivery Note."))
	if not frappe.db.exists("Supplier", {"name": supplier, "disabled": 0}):
		frappe.throw(_("Select an enabled Supplier."))
	trip = _trip_for_delivery_note(dn.name)
	project = project or dn.get("project")
	if not project and trip:
		project = frappe.db.get_value("Delivery Trip", trip, "project")
	warehouse = dn.get("set_warehouse") or next((row.warehouse for row in dn.items if row.warehouse), None)
	rows = []
	for dn_item in dn.items:
		item = frappe.get_cached_doc("Item", dn_item.item_code)
		if not item.is_purchase_item:
			frappe.throw(_("Item {0} is not marked as a purchase item.").format(dn_item.item_code))
		last_rate = frappe.db.get_value("Item", dn_item.item_code, "last_purchase_rate") or 0
		row = {"item_code": dn_item.item_code, "qty": dn_item.qty, "uom": dn_item.uom,
			"stock_uom": dn_item.stock_uom, "conversion_factor": dn_item.conversion_factor,
			"rate": last_rate, "project": dn_item.get("project") or project}
		if item.is_stock_item and (dn_item.get("warehouse") or warehouse):
			row["warehouse"] = dn_item.get("warehouse") or warehouse
		rows.append(row)
	pr = frappe.get_doc({"doctype": "Purchase Receipt", "company": dn.company,
		"supplier": supplier, "posting_date": nowdate(), "currency": dn.currency,
		"conversion_rate": dn.conversion_rate or 1, "project": project,
		"custom_delivery_note": dn.name, "custom_auto_created": 1, "delivery_trip": trip,
		"items": rows}).insert()
	return {"name": pr.name, "link": get_link_to_form("Purchase Receipt", pr.name)}


@frappe.whitelist()
def make_stock_entry_from_purchase_receipt(purchase_receipt, warehouse):
	_require_enabled()
	pr = frappe.get_doc("Purchase Receipt", purchase_receipt)
	if pr.docstatus != 1:
		frappe.throw(_("Purchase Receipt must be submitted."))
	if not frappe.db.exists("Warehouse", {"name": warehouse, "company": pr.company, "is_group": 0, "disabled": 0}):
		frappe.throw(_("Select an enabled warehouse belonging to the company."))
	items = []
	for row in pr.items:
		if frappe.db.get_value("Item", row.item_code, "is_stock_item"):
			items.append({"item_code": row.item_code, "qty": row.qty, "uom": row.uom,
				"conversion_factor": row.conversion_factor, "t_warehouse": warehouse,
				"basic_rate": row.rate, "project": row.project or pr.project})
	if not items:
		frappe.msgprint(_("There are no stock items in this Purchase Receipt."))
		return None
	se = frappe.get_doc({"doctype": "Stock Entry", "company": pr.company,
		"purpose": "Material Receipt", "stock_entry_type": "Material Receipt",
		"posting_date": nowdate(), "project": pr.project,
		"custom_purchase_receipt": pr.name, "delivery_trip": pr.delivery_trip,
		"items": items}).insert()
	return {"name": se.name, "link": get_link_to_form("Stock Entry", se.name)}
