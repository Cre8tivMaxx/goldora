import frappe
from frappe import _


def drop_reference_remark(doc, method=None):
	"""ERPNext's set_remarks() appends a 'Transaction reference no ... dated ...'
	line for every Payment Entry with a reference_no. Business wants that line
	gone from remarks (it shows up as noise in the General Ledger report)."""
	if not doc.reference_no or doc.custom_remarks:
		return

	line = _("Transaction reference no {0} dated {1}").format(doc.reference_no, doc.reference_date)
	doc.remarks = "\n".join(l for l in (doc.remarks or "").split("\n") if l != line)
