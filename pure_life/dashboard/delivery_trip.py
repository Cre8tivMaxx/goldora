import frappe
from frappe import _


def get_data(data=None):
	data = data or {"fieldname": "custom_delivery_trip", "transactions": []}
	if not any(link.get("doctype") == "Vehicle Log" for link in frappe.get_meta("Delivery Trip").links):
		links = data.setdefault("internal_links", {})
		if "Vehicle Log" not in links:
			links["Vehicle Log"] = ["custom_delivery_trip"]
		transactions = data.setdefault("transactions", [])
		if not any("Vehicle Log" in group.get("items", []) for group in transactions):
			transactions.append({"label": _("Reference"), "items": ["Vehicle Log"]})
	return data
