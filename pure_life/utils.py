"""Shared helpers: who receives Fleet Manager alerts, and how they are sent."""

import frappe


def fleet_alert_recipients():
	"""Enabled users chosen in Pure Life Settings; every enabled Fleet Manager while the setting is empty."""
	chosen = [row.user for row in frappe.get_cached_doc("Pure Life Settings").get("fleet_alert_recipients") or [] if row.user]
	if chosen:
		return frappe.get_all("User", filters={"name": ["in", chosen], "enabled": 1}, pluck="name", order_by="name")
	managers = frappe.get_all("Has Role", filters={"role": "Fleet Manager", "parenttype": "User",
		"parent": ["not in", ["Administrator", "Guest"]]}, pluck="parent")
	return frappe.get_all("User", filters={"name": ["in", managers or [""]], "enabled": 1}, pluck="name", order_by="name")


def send_alert(users, subject, message, doctype, name):
	"""Notification Log plus email (when outgoing mail is set up) for each user."""
	# Without an outgoing account sendmail raises and would block the caller; the in-app alert still goes out.
	can_email = frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1})
	for user in dict.fromkeys(u for u in users if u and u != "Guest"):
		frappe.get_doc({"doctype": "Notification Log", "subject": subject, "email_content": message,
			"for_user": user, "type": "Alert", "document_type": doctype, "document_name": name,
			"from_user": "Administrator"}).insert(ignore_permissions=True)
		email = frappe.db.get_value("User", user, "email")
		if email and can_email and frappe.db.get_value("User", user, "enabled"):
			frappe.sendmail(recipients=[email], subject=subject, message=message,
				reference_doctype=doctype, reference_name=name, delayed=True)
