"""Vehicle Log validations for weighbridge records."""

import frappe
from frappe import _


def validate(doc, method=None):
	if doc.empty_weight is not None and doc.loaded_weight is not None and doc.loaded_weight < doc.empty_weight:
		frappe.throw(_("Loaded weight cannot be less than empty weight."))

	for weight_field, document_field in (
		("empty_weight", "empty_weight_doc_no"),
		("loaded_weight", "loaded_weight_doc_no"),
	):
		if doc.get(weight_field) is not None and not doc.get(document_field):
			frappe.throw(_("Enter the document number for the {0}.").format(doc.meta.get_label(weight_field)))
