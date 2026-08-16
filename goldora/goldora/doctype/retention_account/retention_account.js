frappe.ui.form.on("Retention Account", "form_render", function (frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frm.fields_dict.retention_accounts.grid.get_field("retention_account").get_query = function () {
		return {
			filters: {
				account_type: "Receivable",
				company: row.company,
				is_group: 0,
			},
		};
	};
});