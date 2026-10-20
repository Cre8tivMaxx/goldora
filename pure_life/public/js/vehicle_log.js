frappe.ui.form.on("Vehicle Log", {
	setup(frm) {
		frm.set_query("license_plate", () => ({ filters: { disabled: 0 } }));
		frm.set_query("custom_delivery_trip", () => ({
			filters: {
				docstatus: ["<", 2],
				...(frm.doc.license_plate ? { vehicle: frm.doc.license_plate } : {}),
			},
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.custom_documents_attached) {
			frm.dashboard.add_comment(__("Attach the trip documents (tracking form / disposal certificate) and tick Documents Attached."), "red", true);
		}
		// HRMS refuses an Expense Claim without fuel or service costs, so only prompt when there are some.
		const has_expenses = flt(frm.doc.paid_amount) > 0
			|| (frm.doc.service_detail || []).some(row => flt(row.expense_amount) > 0);
		if (frm.doc.docstatus === 1 && has_expenses) {
			frappe.db.exists("Expense Claim", { vehicle_log: frm.doc.name, docstatus: ["<", 2] }).then(exists => {
				if (!exists) {
					const message = __("Please create the Expense Claim for this trip.");
					frm.set_intro(message, "orange");
					pure_life_info_popup(frm, "expense-claim", message, "orange");
				}
			});
		}
	},

	on_submit(frm) {
		if (!frm.doc.custom_documents_attached) pure_life_ask_documents_attached(frm);
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

function pure_life_info_popup(frm, key, message, indicator) {
	const id = `${frm.doctype}:${frm.doc.name}:${key}`;
	window.__pure_life_info_popups ||= new Set();
	if (window.__pure_life_info_popups.has(id)) return;
	window.__pure_life_info_popups.add(id);
	frappe.msgprint({ title: __("Information"), message, indicator });
}

// Mirrors pure_life.vehicle_log.set_totals so the totals update while typing.
function pure_life_set_totals(frm) {
	const d = frm.doc;
	frm.set_value("distance_km", d.odometer && d.last_odometer ? flt(d.odometer) - flt(d.last_odometer) : 0);
	frm.set_value("net_weight", d.loaded_weight && d.empty_weight ? flt(d.loaded_weight) - flt(d.empty_weight) : 0);
	frm.set_value("paid_amount", flt(flt(d.fuel_qty) * flt(d.price), precision("paid_amount")));
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

// Closing the log is when the driver's papers should be in; ask without blocking.
function pure_life_ask_documents_attached(frm) {
	frappe.confirm(__("Have the trip documents (tracking form / disposal certificate) been attached?"),
		() => frappe.db.set_value(frm.doctype, frm.doc.name, "custom_documents_attached", 1).then(() => frm.reload_doc()),
		() => frappe.show_alert({ message: __("Attach the trip documents (tracking form / disposal certificate) and tick Documents Attached."), indicator: "orange" }, 7));
}
