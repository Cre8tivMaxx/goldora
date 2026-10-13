frappe.ui.form.on("Vehicle Log", {
	setup(frm) {
		frm.set_query("custom_delivery_trip", () => ({
			filters: {
				docstatus: ["<", 2],
				...(frm.doc.license_plate ? { vehicle: frm.doc.license_plate } : {}),
			},
		}));
	},
});
