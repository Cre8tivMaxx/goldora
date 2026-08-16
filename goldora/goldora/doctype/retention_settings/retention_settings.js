frappe.ui.form.on("Retention Settings", {
	refresh(frm) {
		frm.set_query("retention_account", "retention_accounts", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return {
				filters: {
					account_type: "Receivable",
					company: row.company,
					is_group: 0,
				},
			};
		});
	},
});
