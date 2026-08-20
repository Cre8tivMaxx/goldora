// Merged with erpnext's journal_entry_list.js (add_fields / get_indicator) — extend, don't replace.
frappe.listview_settings["Journal Entry"] = Object.assign(frappe.listview_settings["Journal Entry"] || {}, {
	// `filters` alone does NOT work here: list_view.js:101 gives view_user_settings.filters
	// absolute priority, and Array.isArray([]) is true — so any saved list view (every user
	// who ever opened this list has one) permanently shadows the default.
	// frappe.route_options is applied on every navigation into the list, so it wins.
	onload: function () {
		frappe.route_options = Object.assign(frappe.route_options || {}, {
			docstatus: ["!=", 2],
		});
	},
	// posting_date sorting is a Property Setter (sort_field/sort_order) — listview_settings has no order_by
});
