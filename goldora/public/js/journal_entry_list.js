// Merged with erpnext's journal_entry_list.js (add_fields / get_indicator) — extend, don't replace.
frappe.listview_settings["Journal Entry"] = Object.assign(frappe.listview_settings["Journal Entry"] || {}, {
	// posting_date sorting is a Property Setter (sort_field/sort_order) — listview_settings has no order_by
	filters: [["docstatus", "!=", 2]],
});
