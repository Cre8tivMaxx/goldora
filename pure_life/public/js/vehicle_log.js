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

	odometer: pure_life_set_totals,
	last_odometer: pure_life_set_totals,
	empty_weight: pure_life_set_totals,
	loaded_weight: pure_life_set_totals,
	fuel_qty: pure_life_set_totals,
	price: pure_life_set_totals,
});

// Mirrors pure_life.vehicle_log.set_totals so the totals update while typing.
function pure_life_set_totals(frm) {
	const d = frm.doc;
	frm.set_value("distance_km", d.odometer && d.last_odometer ? flt(d.odometer) - flt(d.last_odometer) : 0);
	frm.set_value("net_weight", d.loaded_weight && d.empty_weight ? flt(d.loaded_weight) - flt(d.empty_weight) : 0);
	frm.set_value("paid_amount", flt(d.fuel_qty) * flt(d.price));
}

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
