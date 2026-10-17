function start_waste_purchase_receipt(frm) {
	const fields = [
		{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier", reqd: 1, get_query: () => ({ filters: { disabled: 0 } }) },
	];
	if (!frm.doc.project && frappe.meta.get_docfield("Purchase Receipt", "project")?.reqd) {
		fields.push({ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project", reqd: 1 });
	}
	const dialog = new frappe.ui.Dialog({ title: __("هل تم شراء خدمة دفن المخلفات؟"), fields, primary_action_label: __("Yes"), primary_action(values) {
		dialog.hide(); frappe.call({ method: "pure_life.waste_chain.make_purchase_receipt_from_delivery_note", args: { delivery_note: frm.doc.name, ...values },
			callback(r) { if (r.message?.link) frappe.msgprint(r.message.link); } });
	}, secondary_action_label: __("No"), secondary_action() { dialog.hide(); } });
	dialog.show();
}

frappe.ui.form.on("Delivery Note", {
	on_submit(frm) { if (frappe.boot.pure_life_fleet_features) start_waste_purchase_receipt(frm); },
	refresh(frm) {
		if (frappe.boot.pure_life_fleet_features && frm.doc.docstatus === 1 && !frm.doc.__islocal) frappe.db.get_value("Purchase Receipt", { custom_delivery_note: frm.doc.name, docstatus: ["<", 2] }, "name")
			.then(({ message }) => { if (!message?.name) frm.add_custom_button(__("Purchase Receipt"), () => start_waste_purchase_receipt(frm), __("Create")); });
	},
});
