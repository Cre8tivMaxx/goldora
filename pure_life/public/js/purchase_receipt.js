frappe.ui.form.on("Purchase Receipt", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2 && !frm.doc.delivery_trip) {
			frm.add_custom_button(__("Delivery Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "pure_life.delivery_trip.make_delivery_trip_from_purchase_receipt",
					frm,
				});
			}, __("Create"));
		}
	},
});
