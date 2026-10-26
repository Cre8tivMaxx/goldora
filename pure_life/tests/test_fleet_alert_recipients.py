import frappe
from frappe.tests.utils import FrappeTestCase

from pure_life.utils import fleet_alert_recipients


class TestFleetAlertRecipients(FrappeTestCase):
	def make_user(self, roles=(), enabled=1):
		email = frappe.generate_hash(length=8) + "@example.com"
		return frappe.get_doc({"doctype": "User", "email": email, "first_name": "Fleet", "enabled": enabled,
			"send_welcome_email": 0, "roles": [{"role": role} for role in roles]}).insert().name

	def set_recipients(self, users):
		settings = frappe.get_doc("Pure Life Settings")
		settings.set("fleet_alert_recipients", [{"user": user} for user in users])
		settings.save(ignore_permissions=True)

	def setUp(self):
		self.addCleanup(self.set_recipients, [])
		self.set_recipients([])

	def test_empty_setting_falls_back_to_enabled_fleet_managers(self):
		manager = self.make_user(["Fleet Manager"])
		disabled = self.make_user(["Fleet Manager"], enabled=0)
		other = self.make_user()
		users = fleet_alert_recipients()
		self.assertIn(manager, users)
		self.assertNotIn(disabled, users)
		self.assertNotIn(other, users)
		self.assertNotIn("Administrator", users)
		self.assertNotIn("Guest", users)

	def test_filled_setting_returns_only_those_enabled_users(self):
		manager = self.make_user(["Fleet Manager"])
		chosen = self.make_user()
		disabled = self.make_user(enabled=0)
		self.set_recipients([chosen, disabled])
		self.assertEqual(fleet_alert_recipients(), [chosen])
		self.assertNotIn(manager, fleet_alert_recipients())
