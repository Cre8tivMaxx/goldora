function show_waste_link(r) {
	if (r.message && r.message.link) frappe.msgprint(r.message.link);
}

function start_purchase_receipt(frm) {
	const fields = [
		{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier", reqd: 1,
			get_query: () => ({ filters: { disabled: 0 } }) },
		{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item", reqd: 1,
			get_query: () => ({ filters: { disabled: 0, is_purchase_item: 1 } }) },
		{ fieldname: "qty", label: __("Qty"), fieldtype: "Float", default: frm.doc.total_qty, reqd: 1 },
		{ fieldname: "rate", label: __("Rate"), fieldtype: "Currency" },
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project",
			default: frm.doc.project, depends_on: "eval:!doc.project" },
	];
	const dialog = new frappe.ui.Dialog({ title: __("هل تم شراء خدمة دفن المخلفات؟"), fields,
		primary_action_label: __("Yes"), primary_action(values) {
			dialog.hide();
			frappe.call({ method: "pure_life.waste_chain.make_purchase_receipt_from_delivery_note",
				args: { delivery_note: frm.doc.name, ...values }, callback: show_waste_link });
		}, secondary_action_label: __("No"), secondary_action() { dialog.hide(); } });
	dialog.show();
}

frappe.ui.form.on("Delivery Note", {
	on_submit(frm) { if (!frm.__waste_prompted) { frm.__waste_prompted = true; start_purchase_receipt(frm); } },
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.__islocal) {
			frappe.db.get_value("Purchase Receipt", { custom_delivery_note: frm.doc.name, docstatus: ["<", 2] }, "name")
				.then(({ message }) => { if (!message?.name) frm.add_custom_button(__("Purchase Receipt"), () => start_purchase_receipt(frm), __("Create")); });
		}
	},
});

frappe.ui.form.on("Purchase Receipt", {
	on_submit(frm) {
		const dialog = new frappe.ui.Dialog({ title: __("هل توجد مخلفات دخلت المخازن؟"), fields: [
			{ fieldname: "warehouse", label: __("Target Warehouse"), fieldtype: "Link", options: "Warehouse", reqd: 1,
				get_query: () => ({ filters: { company: frm.doc.company, is_group: 0, disabled: 0 } }) },
		], primary_action_label: __("Yes"), primary_action(values) {
			dialog.hide(); frappe.call({ method: "pure_life.waste_chain.make_stock_entry_from_purchase_receipt",
				args: { purchase_receipt: frm.doc.name, warehouse: values.warehouse }, callback: show_waste_link });
		}, secondary_action_label: __("No"), secondary_action() { dialog.hide(); } });
		dialog.show();
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.__islocal) {
			frappe.db.get_value("Stock Entry", { custom_purchase_receipt: frm.doc.name, docstatus: ["<", 2] }, "name")
				.then(({ message }) => { if (!message?.name) frm.add_custom_button(__("Stock Entry"), () => {
					const dialog = new frappe.ui.Dialog({ title: __("هل توجد مخلفات دخلت المخازن؟"), fields: [
						{ fieldname: "warehouse", label: __("Target Warehouse"), fieldtype: "Link", options: "Warehouse", reqd: 1,
							get_query: () => ({ filters: { company: frm.doc.company, is_group: 0, disabled: 0 } }) },
					], primary_action_label: __("Yes"), primary_action(values) { dialog.hide(); frappe.call({ method: "pure_life.waste_chain.make_stock_entry_from_purchase_receipt", args: { purchase_receipt: frm.doc.name, warehouse: values.warehouse }, callback: show_waste_link }); },
					secondary_action_label: __("No"), secondary_action() { dialog.hide(); } }); dialog.show();
				}, __("Create")); });
		}
	},
});
