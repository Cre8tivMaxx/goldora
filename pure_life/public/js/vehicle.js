frappe.ui.form.on("Vehicle", {
	refresh(frm) {
		if (!frm.doc.license_plate || !frm.doc.custom_service_interval_km) return;
		frappe.db.get_list("Vehicle Log", {
			filters: { license_plate: frm.doc.license_plate, docstatus: 1 },
			fields: ["odometer"], order_by: "creation desc", limit: 1,
		}).then(rows => {
			const current = flt(rows?.[0]?.odometer || frm.doc.last_odometer);
			const last_service = flt(frm.doc.custom_last_service_odometer);
			const interval = flt(frm.doc.custom_service_interval_km);
			if (interval > 0 && current - last_service >= interval) {
				frm.set_intro(__("Vehicle service is due: {0} km since the last service.", [current - last_service]), "orange");
			}
		});
	},
});
