frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.docstatus < 2 && !frm.doc.delivery_trip &&
			frm.doc.purpose === "Material Transfer") {
			frm.add_custom_button(__("Delivery Trip"), () => {
				frappe.model.open_mapped_doc({
					method: "pure_life.delivery_trip.make_delivery_trip_from_stock_entry",
					frm,
				});
			}, __("Create"));
		}
	},
});
