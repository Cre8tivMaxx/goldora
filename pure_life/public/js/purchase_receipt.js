function show_stock_entry_prompt(frm) {
	const dialog = new frappe.ui.Dialog({ title: __("هل توجد مخلفات دخلت المخازن؟"), fields: [
		{ fieldname: "warehouse", label: __("Target Warehouse"), fieldtype: "Link", options: "Warehouse", reqd: 1,
			get_query: () => ({ filters: { company: frm.doc.company, is_group: 0, disabled: 0 } }) },
	], primary_action_label: __("Yes"), primary_action(values) {
		dialog.hide(); frappe.call({ method: "pure_life.waste_chain.make_stock_entry_from_purchase_receipt", args: { purchase_receipt: frm.doc.name, warehouse: values.warehouse },
			callback(r) { if (r.message?.link) frappe.msgprint(r.message.link); } });
	}, secondary_action_label: __("No"), secondary_action() { dialog.hide(); } });
	dialog.show();
}

frappe.ui.form.on("Purchase Receipt", {
	on_submit(frm) { show_stock_entry_prompt(frm); },
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2 && !frm.doc.delivery_trip) frm.add_custom_button(__("Delivery Trip"), () => {
			frappe.model.open_mapped_doc({ method: "pure_life.delivery_trip.make_delivery_trip_from_purchase_receipt", frm });
		}, __("Create"));
		if (frm.doc.docstatus === 1 && !frm.doc.__islocal) frappe.db.get_value("Stock Entry", { custom_purchase_receipt: frm.doc.name, docstatus: ["<", 2] }, "name")
			.then(({ message }) => { if (!message?.name) frm.add_custom_button(__("Stock Entry"), () => show_stock_entry_prompt(frm), __("Create")); });
	},
});
