import frappe


def execute():
	"""Drop saved per-user Journal Entry list views.

	frappe/public/js/frappe/list/list_view.js:101 gives view_user_settings.filters
	absolute priority over listview_settings.filters — and Array.isArray([]) is
	true, so even an empty saved filter list permanently shadows the
	`docstatus != 2` default in goldora/public/js/journal_entry_list.js. Anyone
	who had opened the Journal Entry list before this app was installed has such
	a record, which is why the default never appeared for them.

	Clearing them once lets the default take effect. The same rows also hold the
	stale sort order that shadows the posting_date Property Setter.
	"""
	frappe.db.delete("DefaultValue", {"defkey": ("like", "_list_settings:Journal Entry%")})
	frappe.cache.delete_keys("user_settings")
