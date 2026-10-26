import frappe

OLD_NOTIFICATIONS = ["Pure Life DN Email", "Pure Life DN System", "Pure Life PR Email",
	"Pure Life PR System", "Pure Life VL Email", "Pure Life VL System"]


def execute():
	"""These alerts are sent from code now so Pure Life Settings can choose their recipients."""
	for name in OLD_NOTIFICATIONS:
		frappe.delete_doc("Notification", name, ignore_missing=True, force=True)
