"""قائمة التغير فى حقوق الملكية — Statement of Changes in Equity.

One column per equity account of the filtered company (~10 in this client's
chart), one row per movement. Movements are grouped by the counter-account
(GL Entry.against), so no per-company configuration is needed — the trade-off
is that a row is labelled with the counter-account's name rather than the
client's wording (ربح العام / توزيعات أرباح).
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = frappe._dict(filters or {})
	accounts = get_equity_accounts(filters.company)
	if not accounts:
		return get_columns([]), []

	opening = get_balances(filters, accounts, opening=True)
	movements = get_movements(filters, accounts)

	# a dormant equity account would otherwise add an all-zero column
	accounts = [a for a in accounts if opening.get(a) or any(m.get(a) for m in movements.values())]
	if not accounts:
		return get_columns([]), []

	rows = [make_row(_("Opening Balance"), accounts, opening)]
	closing = dict(opening)
	for label, by_account in movements.items():
		rows.append(make_row(label, accounts, by_account))
		for account, amount in by_account.items():
			closing[account] = flt(closing.get(account)) + amount
	rows.append(make_row(_("Closing Balance"), accounts, closing))

	return get_columns(accounts), rows


def get_equity_accounts(company):
	return frappe.get_all(
		"Account",
		filters={"company": company, "root_type": "Equity", "is_group": 0},
		order_by="lft",
		pluck="name",
	)


def _conditions(filters, accounts, opening):
	conditions = ["is_cancelled = 0", "company = %(company)s", "account in %(accounts)s"]
	values = {"company": filters.company, "accounts": accounts, "from_date": filters.from_date}
	if opening:
		conditions.append("posting_date < %(from_date)s")
	else:
		conditions.append("posting_date between %(from_date)s and %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("finance_book"):
		conditions.append("ifnull(finance_book, '') in ('', %(finance_book)s)")
		values["finance_book"] = filters.finance_book
	return " and ".join(conditions), values


# Equity is credit-natured, so credit - debit keeps balances positive.
def get_balances(filters, accounts, opening):
	where, values = _conditions(filters, accounts, opening)
	rows = frappe.db.sql(
		f"""select account, sum(credit - debit) as amount
			from `tabGL Entry` where {where} group by account""",
		values,
		as_dict=True,
	)
	return {d.account: flt(d.amount) for d in rows}


# GL Entry.against holds a comma-joined set() of the voucher's counter accounts
# (journal_entry.py set_against_account), so its order is not stable between
# entries. Sort it so "Cash, Bank" and "Bank, Cash" land on the same row.
def _movement_label(against):
	accounts = sorted(a.strip() for a in (against or "").split(",") if a.strip())
	return ", ".join(accounts) or _("Other")


def get_movements(filters, accounts):
	"""{row label: {account: amount}}, ordered by first appearance."""
	where, values = _conditions(filters, accounts, opening=False)
	rows = frappe.db.sql(
		f"""select account, `against` as against_account, sum(credit - debit) as amount
			from `tabGL Entry` where {where}
			group by account, `against` order by min(posting_date), `against`""",
		values,
		as_dict=True,
	)

	movements = {}
	for d in rows:
		label = _movement_label(d.against_account)
		movements.setdefault(label, {})
		movements[label][d.account] = flt(movements[label].get(d.account)) + flt(d.amount)
	return movements


def make_row(label, accounts, by_account):
	row = {"particulars": label}
	total = 0.0
	for idx, account in enumerate(accounts):
		amount = flt(by_account.get(account))
		row[f"acc_{idx}"] = amount
		total += amount
	row["total"] = total
	return row


def get_columns(accounts):
	columns = [{"label": _("Particulars"), "fieldname": "particulars", "fieldtype": "Data", "width": 260}]
	columns += [
		{"label": account, "fieldname": f"acc_{idx}", "fieldtype": "Currency", "width": 150}
		for idx, account in enumerate(accounts)
	]
	columns.append({"label": _("Total Equity"), "fieldname": "total", "fieldtype": "Currency", "width": 150})
	return columns
