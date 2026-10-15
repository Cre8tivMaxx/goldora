from frappe import _


def add_reverse_link(data, doctype, fieldname):
	"""Show `doctype` (linked back through `fieldname`) in the form's Connections, once."""
	data = dict(data or {})
	data.setdefault("fieldname", fieldname)
	if data["fieldname"] != fieldname:
		data["non_standard_fieldnames"] = {**data.get("non_standard_fieldnames", {}), doctype: fieldname}
	transactions = list(data.get("transactions") or [])
	if not any(doctype in group.get("items", []) for group in transactions):
		transactions.append({"label": _("Reference"), "items": [doctype]})
	data["transactions"] = transactions
	return data
