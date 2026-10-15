import frappe

from pure_life.dashboard import add_reverse_link


def get_data(data=None):
	# Skip when the site already defines this connection as a DocType Link.
	if any(link.get("link_doctype") == "Vehicle Log" for link in frappe.get_meta("Delivery Trip").links):
		return data
	return add_reverse_link(data, "Vehicle Log", "custom_delivery_trip")
