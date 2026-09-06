"""Put the Bank Statement report on the Accounts workspace.

ERPNext ships Financial Reports as a standard workspace, so every `bench migrate`
re-syncs it from erpnext's JSON and drops anything we added. Hence after_migrate
(which runs after that sync) rather than a patch, which would run once and be
silently undone by the next migrate.
"""

import frappe

WORKSPACE = "Financial Reports"
CARD = "Ledgers"
REPORT = "Bank Statement"


def add_bank_statement_link():
	if not frappe.db.exists("Workspace", WORKSPACE) or not frappe.db.exists("Report", REPORT):
		return

	ws = frappe.get_doc("Workspace", WORKSPACE)
	if any(link.link_to == REPORT for link in ws.links):
		return

	card_idx = next((i for i, link in enumerate(ws.links) if _is_card(link, CARD)), None)
	if card_idx is None:
		frappe.log_error(f"'{CARD}' card missing from '{WORKSPACE}'", "Goldora workspace")
		return

	# the card owns every link up to the next Card Break
	insert_at = next(
		(i for i in range(card_idx + 1, len(ws.links)) if ws.links[i].type == "Card Break"),
		len(ws.links),
	)

	# append (not list.insert) so the row gets parent/parentfield set; a bare
	# frappe.get_doc child is silently dropped on save. Then move it into the card.
	ws.append(
		"links",
		{
			"type": "Link",
			"link_type": "Report",
			"link_to": REPORT,
			"label": REPORT,
			"is_query_report": 1,
			"dependencies": "GL Entry",
			"onboard": 0,
			"hidden": 0,
		},
	)
	ws.links.insert(insert_at, ws.links.pop())
	# link_count is what the card renders; a stale value hides the new row
	ws.links[card_idx].link_count = (ws.links[card_idx].link_count or 0) + 1
	for i, link in enumerate(ws.links, start=1):
		link.idx = i

	ws.save(ignore_permissions=True)


def _is_card(link, label):
	return link.type == "Card Break" and link.label == label
