function is_terminal_draft(frm) {
	return !frm.is_new() && frm.doc.docstatus === 0 && ["Completed", "Cancelled"].includes(frm.doc.maintenance_status);
}

frappe.ui.form.on("Asset Maintenance Log", {
	refresh(frm) {
		if (!frm.doc.asset_maintenance) return;
		frappe.db.get_value("Asset Maintenance", frm.doc.asset_maintenance, "custom_vehicle").then(({ message }) => {
			if (!message || !frm.wrapper?.isConnected) return;
			const maintenanceUrl = `/app/asset-maintenance/${encodeURIComponent(frm.doc.asset_maintenance)}`;
			const maintenanceLink = `<a href="${maintenanceUrl}">${frappe.utils.escape_html(frm.doc.asset_maintenance)}</a>`;
			const vehicle = message.custom_vehicle
				? `<a href="/app/vehicle/${encodeURIComponent(message.custom_vehicle)}">${frappe.utils.escape_html(message.custom_vehicle)}</a>`
				: __("No vehicle linked");
			const context = `${__("Maintenance record: {0}", [maintenanceLink])}<br>${__("Vehicle: {0}", [vehicle])}`;
			const terminalDraft = is_terminal_draft(frm);
			frm.set_intro(`${context}${terminalDraft ? `<br>${__("Submit to finish this maintenance.")}` : ""}`, terminalDraft ? "orange" : "blue");
		});
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
