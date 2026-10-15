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
			["customer", "supplier", "address", "stock_entry"].includes(field));
	}
	// Property updates do not invalidate Frappe's cached columns or rendered rows.
	grid.reset_grid();
	pure_life_lock_trip_type(frm);
	frm.ignore_doctypes_on_cancel_all = ["Delivery Note", "Purchase Receipt", "Stock Entry"];
	for (const label of ["Delivery Note", "Purchase Receipt", "Stock Entry"]) {
		if (label !== "Delivery Note" || type !== "Selling") {
			frm.remove_custom_button(__(label), __("Get stops from"));
		}
	}
	if (type !== "Selling") {
		frm.remove_custom_button(__("Notify Customers via Email"));
	}
	if (["Buying", "Warehouse Transfer"].includes(type)) {
		frm.remove_custom_button(__("Delivery Notes"), __("View"));
	}
	if (frm.doc.docstatus === 0 && type === "Selling") {
		frm.add_custom_button(__("Delivery Note"), () => {
			erpnext.utils.map_current_doc({
				method: "erpnext.stock.doctype.delivery_note.delivery_note.make_delivery_trip",
				source_doctype: "Delivery Note", target: frm, date_field: "posting_date",
				setters: { company: frm.doc.company, customer: null },
				get_query_filters: { company: frm.doc.company, status: ["Not In", ["Completed", "Cancelled"]] },
			});
		}, __("Get stops from"));
	}
	if (frm.doc.docstatus !== 0 || !["Buying", "Warehouse Transfer"].includes(type)) return;
	const buying = type === "Buying";
	const suppliers = [...new Set((frm.doc.delivery_stops || []).map(row => row.supplier).filter(Boolean))];
	frm.add_custom_button(__(buying ? "Purchase Receipt" : "Stock Entry"), () => {
		erpnext.utils.map_current_doc({
			method: "pure_life.delivery_trip.make_delivery_trip_from_" + (buying ? "purchase_receipt" : "stock_entry"),
			source_doctype: buying ? "Purchase Receipt" : "Stock Entry",
			target: frm,
			date_field: "posting_date",
			setters: buying ? { supplier: suppliers[0] || null } : {},
			get_query_filters: {
				company: frm.doc.company,
				docstatus: ["<", 2],
				...(buying && suppliers.length ? { supplier: ["in", suppliers] } : {}),
				...(buying ? {} : { purpose: "Material Transfer" }),
			},
		});
	}, __("Get stops from"));
}

function pure_life_trip_guidance(frm) {
	if (frm.doc.docstatus !== 1) return;
	frappe.db.exists("Vehicle Log", { custom_delivery_trip: frm.doc.name, docstatus: ["<", 2] }).then(exists => {
		if (!exists) {
			frm.set_intro(__("Please create the Vehicle Log for this trip."), "orange");
			frm.add_custom_button(__("Vehicle Log"), async () => {
				const employee = frm.doc.driver ? await frappe.db.get_value("Driver", frm.doc.driver, "employee") : null;
				const log = frappe.model.get_new_doc("Vehicle Log");
				Object.assign(log, { custom_delivery_trip: frm.doc.name, license_plate: frm.doc.vehicle,
					date: (frm.doc.departure_time || "").split(" ")[0] || undefined, employee: employee?.message?.employee });
				frappe.set_route("Form", "Vehicle Log", log.name);
			}, __("Create"));
			frm.page.set_inner_btn_group_as_primary(__("Create"));
		} else if (frm.doc.status !== "Completed") {
			frm.set_intro(__("Mark the stops as Visited to complete the trip."), "blue");
		}
	});
}

frappe.ui.form.on("Delivery Trip", {
	refresh(frm) { pure_life_trip_ui(frm); pure_life_trip_guidance(frm); },
	trip_type: pure_life_trip_ui,
	setup(frm) {
		frm.set_query("delivery_note", "delivery_stops", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return {
				filters: {
					company: doc.company,
					docstatus: ["<", 2],
					...(row.customer ? { customer: row.customer } : {}),
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
