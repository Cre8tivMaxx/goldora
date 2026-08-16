frappe.ui.form.on("Retention Account", {
	company(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "retention_account", "");
	},
});
