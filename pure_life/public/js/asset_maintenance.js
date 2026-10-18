frappe.ui.form.on("Asset Maintenance", {
	refresh(frm) {
		if (!frappe.boot.pure_life_fleet_features || !frm.doc.custom_vehicle) return;
		frappe.db.get_value("Vehicle", frm.doc.custom_vehicle, "last_odometer").then(({ message }) => {
			const odometer = flt(message?.last_odometer);
			const due = (frm.doc.asset_maintenance_tasks || []).find(task => flt(task.custom_interval_km) > 0 && odometer - flt(task.custom_last_service_odometer) >= flt(task.custom_interval_km));
			if (due) {
				const message = __("Service due by km: {0}", [due.maintenance_task]);
				frm.set_intro(message, "orange");
				const id = `Asset Maintenance:${frm.doc.name}:service-due`;
				window.__pure_life_info_popups ||= new Set();
				if (!window.__pure_life_info_popups.has(id)) {
					window.__pure_life_info_popups.add(id);
					frappe.msgprint({ title: __("Information"), message, indicator: "orange" });
				}
			}
		});
	}
});
