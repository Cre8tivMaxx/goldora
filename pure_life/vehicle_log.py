"""Vehicle Log weighbridge validations and fuel price defaults."""

import frappe
from frappe import _
from frappe.utils import flt


def validate(doc, method=None):
	if doc.docstatus == 0 and doc.license_plate and frappe.db.get_value("Vehicle", doc.license_plate, "disabled"):
		frappe.throw(_("Vehicle {0} is disabled.").format(doc.license_plate))
	set_fuel_price(doc)
	if flt(doc.fuel_qty) and not flt(doc.price):
		frappe.throw(_("Enter the Fuel Price for the fuel quantity."))
	set_totals(doc)
	if doc.empty_weight is not None and doc.loaded_weight is not None and doc.loaded_weight < doc.empty_weight:
		frappe.throw(_("Loaded weight cannot be less than empty weight."))

	for weight_field, document_field in (
		("empty_weight", "empty_weight_doc_no"),
		("loaded_weight", "loaded_weight_doc_no"),
	):
		if doc.get(weight_field) is not None and not doc.get(document_field):
			frappe.throw(_("Enter the document number for the {0}.").format(doc.meta.get_label(weight_field)))


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
			users = [task.get("assign_to")]
			users += frappe.get_all("Has Role", filters={"role": "Fleet Manager", "parenttype": "User"}, pluck="parent")
			for user in dict.fromkeys(u for u in users if u and u != "Guest"):
				frappe.get_doc({"doctype": "Notification Log", "subject": message, "email_content": message,
					"for_user": user, "type": "Alert", "document_type": "Vehicle Log", "document_name": doc.name,
					"from_user": "Administrator"}).insert(ignore_permissions=True)
				email = frappe.db.get_value("User", user, "email")
				if email and frappe.db.get_value("User", user, "enabled"):
					frappe.sendmail(recipients=[email], subject=message, message=message,
						reference_doctype="Vehicle Log", reference_name=doc.name, delayed=True)
			task.db_set("custom_km_alert_sent_at", odometer, update_modified=False)


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
