from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from goldora.workspace import CARD, REPORT, WORKSPACE, add_bank_statement_link


class TestAddBankStatementLink(FrappeTestCase):
	"""ERPNext re-syncs Financial Reports from its own JSON on every migrate, so
	this runs from after_migrate and must be safe to run over and over."""

	def setUp(self):
		if not frappe.db.exists("Workspace", WORKSPACE):
			self.skipTest(f"'{WORKSPACE}' workspace not installed")
		if not frappe.db.exists("Report", REPORT):
			self.skipTest(f"'{REPORT}' report not installed")
		# Workspace.on_update writes the doc back into erpnext's app folder when
		# developer_mode is on; a test must not edit another app's source
		conf = patch.dict(frappe.conf, {"developer_mode": 0})
		conf.start()
		self.addCleanup(conf.stop)

	def _links(self):
		return [(link.type, link.label) for link in frappe.get_doc("Workspace", WORKSPACE).links]

	def test_lands_inside_the_ledgers_card(self):
		add_bank_statement_link()
		links = self._links()

		card = links.index(("Card Break", CARD))
		position = links.index(("Link", REPORT))
		next_card = next((i for i in range(card + 1, len(links)) if links[i][0] == "Card Break"), len(links))
		self.assertLess(card, position)
		self.assertLessEqual(position, next_card)

	def test_bumps_the_card_link_count(self):
		ws = frappe.get_doc("Workspace", WORKSPACE)
		card = next(i for i, link in enumerate(ws.links) if (link.type, link.label) == ("Card Break", CARD))
		before = ws.links[card].link_count or 0

		add_bank_statement_link()

		# a stale link_count means the card renders without the new row
		self.assertEqual(frappe.get_doc("Workspace", WORKSPACE).links[card].link_count, before + 1)

	def test_is_idempotent(self):
		add_bank_statement_link()
		once = self._links()
		add_bank_statement_link()
		self.assertEqual(self._links(), once)
