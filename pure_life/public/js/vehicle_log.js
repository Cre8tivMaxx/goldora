frappe.ui.form.on("Vehicle Log", {
	setup(frm) {
		frm.set_query("custom_delivery_trip", () => ({
			filters: {
				docstatus: ["<", 2],
				...(frm.doc.license_plate ? { vehicle: frm.doc.license_plate } : {}),
			},
		}));
	},

	license_plate(frm) {
		pure_life_set_fuel_price(frm);
	},

	date(frm) {
		pure_life_set_fuel_price(frm);
	},
});

// Default the fuel price to the last price used for this fuel type; keep a price the user typed.
function pure_life_set_fuel_price(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.license_plate) return;
	if (frm.doc.price && frm.doc.price !== frm._pure_life_auto_price) return;

	frappe.call({
		method: "pure_life.vehicle_log.get_last_fuel_price",
		args: { license_plate: frm.doc.license_plate, date: frm.doc.date, exclude: frm.is_new() ? null : frm.doc.name },
		callback(r) {
			if (!r.message) return;
			frm._pure_life_auto_price = r.message;
			frm.set_value("price", r.message);
		},
	});
}
