"""Vehicle Log weighbridge validations and fuel price defaults."""

import frappe
from frappe import _
from frappe.utils import flt

from pure_life.utils import fleet_alert_recipients, send_alert

TRIP_DOCUMENT_RECIPIENTS = {
	"Selling": ("Sales Manager", "Delivery Note", "delivery_note"),
	"Buying": ("Purchase Manager", "Purchase Receipt", "purchase_receipt"),
	"Warehouse Transfer": ("Stock Manager", "Stock Entry", "stock_entry"),
}


def validate(doc, method=None):
	if doc.docstatus == 0 and doc.license_plate and frappe.db.get_value("Vehicle", doc.license_plate, "disabled"):
		frappe.throw(_("Vehicle {0} is disabled.").format(doc.license_plate))
	set_fuel_price(doc)
	if flt(doc.fuel_qty) and not flt(doc.price):
		frappe.throw(_("Enter the Fuel Price for the fuel quantity."))
	set_totals(doc)
	if flt(doc.empty_weight) and flt(doc.loaded_weight) and flt(doc.loaded_weight) < flt(doc.empty_weight):
		frappe.throw(_("Loaded weight cannot be less than empty weight."))

	for weight_field, document_field in (
		("empty_weight", "empty_weight_doc_no"),
		("loaded_weight", "loaded_weight_doc_no"),
	):
		# Unset weights come back as 0 once saved, so only a real weight needs its document.
		if flt(doc.get(weight_field)) and not doc.get(document_field):
			frappe.throw(_("Enter the document number for the {0}.").format(doc.meta.get_label(weight_field)))
	if flt(doc.loaded_weight) > 0 and not (doc.get("custom_waste_description") or "").strip():
		frappe.throw(_("Enter the Waste Description."))


def validate_vehicle_log_expense_claim(doc, method=None):
	if doc.vehicle_log and not doc.employee:
		frappe.throw(_("Set an Employee on Vehicle Log {0} before creating its Expense Claim.").format(doc.vehicle_log))


def set_totals(doc, method=None):
	doc.distance_km = flt(doc.odometer) - flt(doc.last_odometer) if doc.odometer and doc.last_odometer else 0
	doc.net_weight = flt(doc.loaded_weight) - flt(doc.empty_weight) if doc.loaded_weight and doc.empty_weight else 0
	doc.paid_amount = flt(flt(doc.fuel_qty) * flt(doc.price), doc.precision("paid_amount"))


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


def on_submit(doc, method=None):
	if not doc.license_plate or not frappe.conf.get("pure_life_fleet_features"):
		return
	odometer = flt(doc.odometer)
	for am_name in frappe.get_all("Asset Maintenance", filters={"custom_vehicle": doc.license_plate}, pluck="name"):
		am = frappe.get_doc("Asset Maintenance", am_name)
		for task in am.asset_maintenance_tasks:
			interval = flt(task.get("custom_interval_km"))
			last = flt(task.get("custom_last_service_odometer"))
			if interval <= 0 or odometer - last < interval or flt(task.get("custom_km_alert_sent_at")) >= last + interval:
				continue
			message = _("Vehicle {0} has exceeded {1} km since the last {2}.").format(doc.license_plate, int(odometer-last), task.maintenance_task)
			send_alert([task.get("assign_to"), *fleet_alert_recipients()], message, message, "Vehicle Log", doc.name)
			task.db_set("custom_km_alert_sent_at", odometer, update_modified=False)


def notify_closed(doc, method=None):
	"""Tell the Fleet Alert Recipients that a Vehicle Log was closed (submitted)."""
	if doc.custom_delivery_trip:
		subject = _("Vehicle Log {0} closed for trip {1}").format(doc.name, doc.custom_delivery_trip)
		message = _("Vehicle Log {0} closed for vehicle {1} - trip {2}. Review the vehicle data and update the Delivery Note.").format(
			doc.name, doc.license_plate, doc.custom_delivery_trip)
	else:
		subject = _("Vehicle Log {0} closed").format(doc.name)
		message = _("Vehicle Log {0} closed for vehicle {1}. Review the vehicle data and update the Delivery Note.").format(
			doc.name, doc.license_plate)
	send_alert(fleet_alert_recipients(), subject, message, "Vehicle Log", doc.name)


def notify_other_movements(doc, method=None):
	"""Other Movements trips have no documents to hand over; the Fleet Alert Recipients hear when the log is submitted."""
	if not frappe.conf.get("pure_life_fleet_features") or not doc.custom_delivery_trip:
		return
	if frappe.db.get_value("Delivery Trip", doc.custom_delivery_trip, "trip_type") != "Other Movements":
		return
	message = _("Vehicle Log {0} submitted for Other Movements trip {1}").format(doc.name, doc.custom_delivery_trip)
	send_alert(fleet_alert_recipients(), message, message, "Vehicle Log", doc.name)


def documents_attached_changed(doc, method=None):
	if not frappe.conf.get("pure_life_fleet_features") or not doc.has_value_changed("custom_documents_attached") or not doc.custom_documents_attached or not doc.custom_delivery_trip:
		return
	trip = frappe.get_doc("Delivery Trip", doc.custom_delivery_trip)
	config = TRIP_DOCUMENT_RECIPIENTS.get(trip.trip_type)
	if not config:
		return
	role, doctype, field = config
	message = _("Vehicle Log {0} closed and documents attached for trip {1}").format(doc.name, trip.name)
	documents = list(dict.fromkeys(stop.get(field) for stop in trip.delivery_stops if stop.get(field)))
	users = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User",
		"parent": ["not in", ["Administrator", "Guest"]]}, pluck="parent")
	users = frappe.get_all("User", filters={"name": ["in", users or [""]], "enabled": 1}, pluck="name")
	can_email = frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1})
	for name in documents:
		for user in users:
			frappe.get_doc({"doctype": "Notification Log", "subject": message, "email_content": message,
				"for_user": user, "type": "Alert", "document_type": doctype,
				"document_name": name, "from_user": "Administrator"}).insert(ignore_permissions=True)
			email = frappe.db.get_value("User", user, "email")
			if can_email and email:
				frappe.sendmail(recipients=[email], subject=message, message=message,
					reference_doctype=doctype,
					reference_name=name, delayed=True)


def maintenance_log_on_submit(doc, method=None):
	if not frappe.conf.get("pure_life_fleet_features") or doc.maintenance_status != "Completed":
		return
	am_name = doc.asset_maintenance
	if not am_name:
		return
	am = frappe.get_doc("Asset Maintenance", am_name)
	task = next((t for t in am.asset_maintenance_tasks if t.name == doc.task), None)
	if not task:
		return
	odometer = frappe.db.get_value("Vehicle", am.custom_vehicle, "last_odometer") or 0
	latest = frappe.get_all("Vehicle Log", filters={"license_plate": am.custom_vehicle, "docstatus": 1}, fields=["odometer"], order_by="creation desc", limit=1)
	if latest:
		odometer = latest[0].odometer
	task.db_set({"custom_last_service_odometer": odometer, "custom_km_alert_sent_at": 0}, update_modified=False)


# Expense Claim Type the Vehicle Log claim is filed under, when the site defines it.
VEHICLE_EXPENSE_TYPE = "مصاريف المركبات"


@frappe.whitelist()
def make_expense_claim(docname):
	from hrms.hr.doctype.vehicle_log.vehicle_log import make_expense_claim as make_hrms_expense_claim

	claim = make_hrms_expense_claim(docname)
	if frappe.db.exists("Expense Claim Type", VEHICLE_EXPENSE_TYPE):
		for row in claim.get("expenses", []):
			row["expense_type"] = row.get("expense_type") or VEHICLE_EXPENSE_TYPE
	return claim
