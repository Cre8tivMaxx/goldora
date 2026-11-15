function is_terminal_draft(frm) {
	return !frm.is_new() && frm.doc.docstatus === 0 && ["Completed", "Cancelled"].includes(frm.doc.maintenance_status);
}

frappe.ui.form.on("Asset Maintenance Log", {
	refresh(frm) {
		if (is_terminal_draft(frm)) {
			frm.set_intro(__("Submit to finish this maintenance."), "orange");
		}
	},
	after_save(frm) {
		if (!is_terminal_draft(frm) || frm.__pure_life_submit_prompt_shown) return;
		frm.__pure_life_submit_prompt_shown = true;
		frappe.confirm(
			__("This maintenance is saved as {0}. Submit it to finish and update the maintenance schedule?", [frm.doc.maintenance_status]),
			() => frm.savesubmit(),
			() => frm.refresh()
		);
	}
});
