frappe.ui.form.on("Sales Invoice", {
	setup(frm) {
		frm.__retention_companies = null;
	},

	onload(frm) {
		frappe.call({
			method: "goldora.retention.get_retention_companies",
			callback(r) {
				frm.__retention_companies = r.message || [];
				toggle_retention_section(frm);
			},
		});
	},

	refresh(frm) {
		toggle_retention_section(frm);
	},

	company(frm) {
		toggle_retention_section(frm);
	},

	custom_apply_retention(frm) {
		refresh_retention_amount(frm);
	},

	custom_retention_percent(frm) {
		refresh_retention_amount(frm);
	},
});

function toggle_retention_section(frm) {
	if (!Array.isArray(frm.__retention_companies)) return;
	const available = frm.__retention_companies.includes(frm.doc.company);
	frm.toggle_display("custom_retention_section", available);
	if (!available && frm.doc.docstatus === 0 && frm.doc.custom_apply_retention) {
		frm.set_value("custom_apply_retention", 0);
	}
}

function refresh_retention_amount(frm) {
	if (!frm.doc.custom_apply_retention) {
		frm.set_value("custom_retention_amount", 0);
		return;
	}
	const amount = flt(
		(frm.doc.net_total * flt(frm.doc.custom_retention_percent)) / 100,
		precision("custom_retention_amount", frm.doc)
	);
	frm.set_value("custom_retention_amount", amount);
}