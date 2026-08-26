import frappe
from frappe import _
from frappe.utils import flt

INTERCOMPANY_PARTY_TYPES = ("Customer", "Supplier")


def get_intercompany_rows(doc):
	"""Rows whose party represents another company. Empty unless the source
	company has inter-company JEs switched on (off by default)."""
	if not frappe.get_cached_value("Company", doc.company, "custom_enable_intercompany_je"):
		return []

	rows = []
	for row in doc.accounts:
		if row.party_type not in INTERCOMPANY_PARTY_TYPES or not row.party:
			continue
		target_company = frappe.get_cached_value(row.party_type, row.party, "represents_company")
		if target_company and target_company != doc.company:
			rows.append((row, target_company))
	return rows


INTERNAL_FLAG = {"Customer": "is_internal_customer", "Supplier": "is_internal_supplier"}


def _get_reciprocal_party(source_company, party_type):
	return frappe.db.get_value(
		party_type,
		{"represents_company": source_company, INTERNAL_FLAG[party_type]: 1},
		"name",
		order_by="creation",
	)


def _get_suspense_account(target_company):
	return frappe.get_cached_value("Company", target_company, "custom_intercompany_suspense_account")


def _check_target_company(doc, target_company, party_type):
	"""Return an error message if target_company isn't ready for a counterpart, else None."""
	if not _get_reciprocal_party(doc.company, party_type):
		return _("Company {0} has no internal {1} representing {2}.").format(
			target_company, party_type, doc.company
		)

	if not _get_suspense_account(target_company):
		return _("Company {0} has no Inter-company Suspense Account configured.").format(target_company)

	# every field book() reads must be checked here — a blank one would otherwise
	# blow up inside on_submit and roll back the accountant's own entry
	party_account_field = "default_payable_account" if party_type == "Supplier" else "default_receivable_account"
	for field, label in ((party_account_field, _("default party account")), ("cost_center", _("default cost center"))):
		if not frappe.get_cached_value("Company", target_company, field):
			return _("Company {0} has no {1} configured.").format(target_company, label)

	source_currency = frappe.get_cached_value("Company", doc.company, "default_currency")
	target_currency = frappe.get_cached_value("Company", target_company, "default_currency")
	if target_currency != source_currency:
		return _("Company {0} and {1} use different currencies.").format(doc.company, target_company)

	return None


def _net_by_company(doc, precision):
	"""Net debit-minus-credit per target company, mirroring how book() decides."""
	by_company = {}
	for row, target_company in get_intercompany_rows(doc):
		by_company.setdefault(target_company, []).append(row)

	return {
		company: flt(
			sum(flt(r.debit_in_account_currency) - flt(r.credit_in_account_currency) for r in rows),
			precision,
		)
		for company, rows in by_company.items()
	}


def validate(doc, method=None):
	"""Warn — never block — on config gaps. The accountant's own JE must always be saveable."""
	if not doc.get("custom_create_intercompany_je", 1) or _live_counterpart(doc):
		return

	warnings = []
	for target_company, net in _net_by_company(doc, doc.precision("debit_in_account_currency", "accounts")).items():
		if not net:
			continue
		message = _check_target_company(doc, target_company, "Supplier" if net > 0 else "Customer")
		if message:
			warnings.append(message)

	if warnings:
		frappe.msgprint(
			"<br>".join(dict.fromkeys(warnings)),
			title=_("Inter-company counterpart skipped"),
			indicator="orange",
		)


def _live_counterpart(doc):
	"""The linked counterpart, if it still exists. A dangling link is treated as none."""
	ref = doc.get("inter_company_journal_entry_reference")
	return ref if ref and frappe.db.exists("Journal Entry", ref) else None


def book(doc, method=None):
	if not doc.get("custom_create_intercompany_je", 1):
		return

	if _live_counterpart(doc):
		return

	precision = doc.precision("debit_in_account_currency", "accounts")
	created = []

	for target_company, net in _net_by_company(doc, precision).items():
		if not net:
			continue

		party_type = "Supplier" if net > 0 else "Customer"
		message = _check_target_company(doc, target_company, party_type)
		if message:
			frappe.msgprint(
				_("Inter-company counterpart for {0} was not created: {1}").format(target_company, message),
				title=_("Inter-company counterpart skipped"),
				indicator="orange",
			)
			continue

		cost_center = frappe.get_cached_value("Company", target_company, "cost_center")
		suspense_account = _get_suspense_account(target_company)
		party = _get_reciprocal_party(doc.company, party_type)

		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = target_company
		je.posting_date = doc.posting_date
		je.user_remark = _("Inter-company counterpart of Journal Entry {0}").format(doc.name)

		if net > 0:
			# source is owed by target -> target owes a payable to source
			account = frappe.get_cached_value("Company", target_company, "default_payable_account")
			je.append(
				"accounts",
				{
					"account": account,
					"party_type": "Supplier",
					"party": party,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": net,
					"cost_center": cost_center,
				},
			)
			je.append(
				"accounts",
				{
					"account": suspense_account,
					"debit_in_account_currency": net,
					"credit_in_account_currency": 0,
					"cost_center": cost_center,
				},
			)
		else:
			amount = flt(-net, precision)
			account = frappe.get_cached_value("Company", target_company, "default_receivable_account")
			je.append(
				"accounts",
				{
					"account": account,
					"party_type": "Customer",
					"party": party,
					"debit_in_account_currency": amount,
					"credit_in_account_currency": 0,
					"cost_center": cost_center,
				},
			)
			je.append(
				"accounts",
				{
					"account": suspense_account,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount,
					"cost_center": cost_center,
				},
			)

		je.inter_company_journal_entry_reference = doc.name
		je.insert(ignore_permissions=True)
		created.append(je.name)

	if created:
		# only the first counterpart is linked back on the source; multiple
		# counterparts may still be created, each pointing back at doc.name
		doc.db_set("inter_company_journal_entry_reference", created[0])


def unbook(doc, method=None):
	# The link is symmetric (book() writes it on both sides), so pointing at us is not
	# enough — on a counterpart that also matches the source, and acting on it would
	# either deadlock the cancel or delete the accountant's original entry. A
	# counterpart is always inserted during its source's on_submit, so it is the
	# strictly newer of the pair.
	# ponytail: creation order as the direction marker; a dedicated "is counterpart"
	# field would be sturdier if the link ever gets written by anything but book().
	counterparts = frappe.get_all(
		"Journal Entry",
		filters={
			"inter_company_journal_entry_reference": doc.name,
			"creation": (">", doc.creation),
			"docstatus": ("<", 2),
		},
		fields=["name", "company", "docstatus"],
	)

	for counterpart in counterparts:
		if counterpart.docstatus == 1:
			frappe.throw(
				_("Inter-company counterpart {0} is submitted. Cancel it in {1} first.").format(
					counterpart.name, counterpart.company
				)
			)

	if doc.get("inter_company_journal_entry_reference"):
		doc.db_set("inter_company_journal_entry_reference", None)

	# and drop the source's link to us, or frappe refuses the cancel with LinkExistsError
	for source in frappe.get_all(
		"Journal Entry",
		filters={"inter_company_journal_entry_reference": doc.name, "creation": ("<", doc.creation)},
		pluck="name",
	):
		frappe.db.set_value("Journal Entry", source, "inter_company_journal_entry_reference", None)

	for counterpart in counterparts:
		frappe.delete_doc("Journal Entry", counterpart.name, ignore_permissions=True)