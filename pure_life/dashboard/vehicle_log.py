from hrms.hr.doctype.expense_claim.expense_claim_dashboard import get_data as get_expense_claim_data


def get_data(data=None):
	data = data or get_expense_claim_data()
	links = data.setdefault("internal_links", {})
	if "Expense Claim" not in links:
		links["Expense Claim"] = ["vehicle_log"]
	transactions = data.setdefault("transactions", [])
	if not any("Expense Claim" in group.get("items", []) for group in transactions):
		transactions.append({"label": "Reference", "items": ["Expense Claim"]})
	return data
