function pure_life_lock_trip_type(frm) {
	// Frappe initializes required tables with an empty row on new forms.
	const has_stops = (frm.doc.delivery_stops || []).some(row =>
		row.customer || row.supplier || row.address || row.delivery_note || row.purchase_receipt || row.stock_entry);
	frm.set_df_property("trip_type", "read_only", frm.doc.docstatus !== 0 || (!!frm.doc.trip_type && has_stops));
}

function pure_life_trip_ui(frm) {
	const type = frm.doc.trip_type;
	const visible = {
		Selling: ["customer", "address", "delivery_note"],
		Buying: ["supplier", "address", "purchase_receipt"],
		"Warehouse Transfer": ["stock_entry", "source_warehouse", "target_warehouse"],
	}[type] || [];
	const grid = frm.fields_dict.delivery_stops.grid;
	for (const field of ["customer", "supplier", "address", "delivery_note", "purchase_receipt",
		"stock_entry", "source_warehouse", "target_warehouse"]) {
		grid.update_docfield_property(field, "hidden", !visible.includes(field));
		grid.update_docfield_property(field, "in_list_view", visible.includes(field));
		grid.update_docfield_property(field, "reqd", visible.includes(field) &&
			["customer", "supplier", "address", "stock_entry", "delivery_note"].includes(field));
	}
	// Property updates do not invalidate Frappe's cached columns or rendered rows.
	grid.reset_grid();
	pure_life_lock_trip_type(frm);
	frm.ignore_doctypes_on_cancel_all = ["Delivery Note", "Purchase Receipt", "Stock Entry"];
	// Drop ERPNext's own buttons; ours (below) filter by the trip's parties.
	for (const label of ["Delivery Note", "Purchase Receipt", "Stock Entry"]) {
		frm.remove_custom_button(__(label), __("Get stops from"));
	}
	if (type !== "Selling") {
		frm.remove_custom_button(__("Notify Customers via Email"));
	}
	if (["Buying", "Warehouse Transfer"].includes(type)) {
		frm.remove_custom_button(__("Delivery Notes"), __("View"));
	}
	if (frm.doc.docstatus === 0 && type === "Selling") {
		frm.add_custom_button(__("Delivery Note"), () => {
			// Limit to the customers already on the stops.
			const customers = [...new Set((frm.doc.delivery_stops || []).map(row => row.customer).filter(Boolean))];
			erpnext.utils.map_current_doc({
				method: "erpnext.stock.doctype.delivery_note.delivery_note.make_delivery_trip",
				source_doctype: "Delivery Note", target: frm, date_field: "posting_date",
				setters: { company: frm.doc.company, customer: customers.length === 1 ? customers[0] : null },
				get_query_filters: {
					company: frm.doc.company,
					docstatus: ["<", 2],
					status: ["Not In", ["Completed", "Cancelled"]],
					...(customers.length ? { customer: ["in", customers] } : {}),
				},
			});
		}, __("Get stops from"));
	}
	if (frm.doc.docstatus !== 0 || !["Buying", "Warehouse Transfer"].includes(type)) return;
	const buying = type === "Buying";
	const suppliers = [...new Set((frm.doc.delivery_stops || []).map(row => row.supplier).filter(Boolean))];
	frm.add_custom_button(__(buying ? "Purchase Receipt" : "Stock Entry"), async () => {
		// Receipts already linked to this trip win; otherwise limit to the stops' suppliers.
		const linked = buying && !frm.is_new() && await frappe.db.count("Purchase Receipt",
			{ filters: { delivery_trip: frm.doc.name, docstatus: ["<", 2] } });
		const supplier_filter = linked ? { delivery_trip: frm.doc.name }
			: suppliers.length ? { supplier: ["in", suppliers] } : {};
		erpnext.utils.map_current_doc({
			method: "pure_life.delivery_trip.make_delivery_trip_from_" + (buying ? "purchase_receipt" : "stock_entry"),
			source_doctype: buying ? "Purchase Receipt" : "Stock Entry",
			target: frm,
			date_field: "posting_date",
			setters: buying ? { supplier: !linked && suppliers.length === 1 ? suppliers[0] : null } : {},
			get_query_filters: {
				company: frm.doc.company,
				docstatus: ["<", 2],
				...(buying ? supplier_filter : { purpose: "Material Transfer" }),
			},
		});
	}, __("Get stops from"));
}

async function pure_life_new_vehicle_log(frm) {
	const employee = frm.doc.driver ? await frappe.db.get_value("Driver", frm.doc.driver, "employee") : null;
	// Defaults such as the naming series need the Vehicle Log meta loaded first.
	await frappe.model.with_doctype("Vehicle Log");
	const log = frappe.model.get_new_doc("Vehicle Log");
	Object.assign(log, { custom_delivery_trip: frm.doc.name, license_plate: frm.doc.vehicle,
		date: (frm.doc.departure_time || "").split(" ")[0] || undefined, employee: employee?.message?.employee });
	frappe.set_route("Form", "Vehicle Log", log.name);
}

// A trip is submitted only after its Vehicle Log exists; offer to create it prefilled.
async function pure_life_require_vehicle_log(frm) {
	if (!frappe.boot.pure_life_fleet_features) return;
	const exists = await frappe.db.exists("Vehicle Log", { custom_delivery_trip: frm.doc.name, docstatus: ["<", 2] });
	if (exists) {
		const attached = await frappe.db.get_value("Vehicle Log", exists, "custom_documents_attached");
		if (attached?.message?.custom_documents_attached) return;
		frappe.validated = false;
		frappe.msgprint({ title: __("Documents Attached"), indicator: "orange",
			message: __("Attach the trip documents and tick Documents Attached before submitting.") +
			` <button class="btn btn-primary btn-sm" onclick="frappe.set_route('Form','Vehicle Log','${exists}')">${__("Open Vehicle Log")}</button>` });
		return;
	}
	frappe.validated = false;
	frappe.confirm(__("Please create the Vehicle Log for this trip before submitting it. Create it now?"),
		() => pure_life_new_vehicle_log(frm));
}

function pure_life_trip_guidance(frm) {
	if (frm.doc.docstatus !== 1) return;
	frappe.db.exists("Vehicle Log", { custom_delivery_trip: frm.doc.name, docstatus: ["<", 2] }).then(async exists => {
		if (!exists) {
			const message = __("Please create the Vehicle Log for this trip.");
			frm.set_intro(message, "orange");
			pure_life_info_popup(frm, "vehicle-log", message, "orange");
			frm.add_custom_button(__("Vehicle Log"), () => pure_life_new_vehicle_log(frm), __("Create"));
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		} else if (frm.doc.status !== "Completed") {
			const result = await frappe.db.get_value("Vehicle Log", exists, "custom_documents_attached");
			if (!result?.message?.custom_documents_attached) {
				const message = __("Attach the trip documents and tick Documents Attached in the Vehicle Log.");
				frm.set_intro(message, "orange");
				pure_life_info_popup(frm, "attach-documents", message, "orange");
				frm.add_custom_button(__("Vehicle Log"), () => frappe.set_route("Form", "Vehicle Log", exists));
				return;
			}
			const message = __("Mark the stops as Visited to complete the trip.");
			frm.set_intro(message, "blue");
			pure_life_info_popup(frm, "visit-stops", message, "blue");
		}
	});
}

function pure_life_info_popup(frm, key, message, indicator) {
	const id = `${frm.doctype}:${frm.doc.name}:${key}`;
	window.__pure_life_info_popups ||= new Set();
	if (window.__pure_life_info_popups.has(id)) return;
	window.__pure_life_info_popups.add(id);
	frappe.msgprint({ title: __("Information"), message, indicator });
}

frappe.ui.form.on("Delivery Trip", {
	refresh(frm) { pure_life_trip_ui(frm); pure_life_trip_guidance(frm); },
	before_submit: pure_life_require_vehicle_log,
	trip_type: pure_life_trip_ui,
	setup(frm) {
		frm.set_query("delivery_note", "delivery_stops", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {
				filters: {
					company: doc.company,
					docstatus: ["<", 2],
					...(row.customer ? { customer: row.customer } : { name: "__no_matching_customer__" }),
				},
			};
		});
		frm.set_query("purchase_receipt", "delivery_stops", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {
				filters: {
					company: doc.company,
					docstatus: ["<", 2],
					...(row.supplier ? { supplier: row.supplier } : {}),
				},
			};
		});
		frm.set_query("vehicle", () => ({ filters: { disabled: 0 } }));
		frm.set_query("stock_entry", "delivery_stops", doc => ({
			filters: {
				company: doc.company,
				docstatus: ["<", 2],
				purpose: "Material Transfer",
			},
		}));
		frm.set_query("customer", "delivery_stops", { disabled: 0 });
		frm.set_query("supplier", "delivery_stops", { disabled: 0 });
		for (const field of ["address", "contact"]) {
			frm.set_query(field, "delivery_stops", (doc, cdt, cdn) => {
				const row = locals[cdt][cdn];
				const party = row.supplier ? "Supplier" : "Customer";
				return {
					query: `frappe.contacts.doctype.${field}.${field}.${field}_query`,
					filters: { link_doctype: party, link_name: row.supplier || row.customer },
				};
			});
		}
	},
});

frappe.ui.form.on("Delivery Stop", {
	delivery_stops_add: pure_life_trip_ui,
	delivery_stops_remove: pure_life_trip_ui,
	delivery_stops_delete: pure_life_lock_trip_type,
	customer: pure_life_lock_trip_type,
	address: pure_life_lock_trip_type,
	delivery_note: pure_life_lock_trip_type,
	purchase_receipt: pure_life_lock_trip_type,
	stock_entry: pure_life_lock_trip_type,
	async supplier(frm, cdt, cdn) {
		pure_life_lock_trip_type(frm);
		const row = locals[cdt][cdn];
		const supplier = row.supplier;
		const result = supplier ? await frappe.call({
			method: "pure_life.delivery_trip.get_supplier_contact_and_address",
			args: { supplier },
		}) : { message: {} };
		if (row.supplier !== supplier) return;
		await frappe.model.set_value(cdt, cdn, {
			address: result.message.address || "",
			contact: result.message.contact || "",
		});
	},
});
