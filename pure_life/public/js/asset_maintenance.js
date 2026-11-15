frappe.ui.form.on("Asset Maintenance", {
	refresh(frm) {
		if (!frappe.boot.pure_life_fleet_features || !frm.doc.custom_vehicle) return;
		frappe.db.get_value("Vehicle", frm.doc.custom_vehicle, "last_odometer").then(({ message }) => {
			const odometer = flt(message?.last_odometer);
			const kmTasks = (frm.doc.asset_maintenance_tasks || []).filter(task => flt(task.custom_interval_km) > 0);
			const due = kmTasks.find(task => odometer - flt(task.custom_last_service_odometer) >= flt(task.custom_interval_km));
			if (!due) return;
			const vehicleMessage = __("Service due by km: {0}", [due.maintenance_task]);
			frappe.db.get_list("Asset Maintenance Log", {
				filters: {
					asset_maintenance: frm.doc.name,
					task: ["in", kmTasks.map(task => task.name)],
					maintenance_status: ["in", ["Completed", "Cancelled"]],
					docstatus: 0
				},
				fields: ["name", "task", "maintenance_status"],
				limit: 100
			}).then(logs => {
				const draft = (logs || []).find(log => log.task === due.name);
				const html = draft
					? `${vehicleMessage}<br><a href="/app/asset-maintenance-log/${encodeURIComponent(draft.name)}">${__("{0} is saved but not submitted — submit it to clear this alert", [draft.name])}</a>`
					: vehicleMessage;
				frm.set_intro(html, "orange");
				const id = `Asset Maintenance:${frm.doc.name}:service-due`;
				window.__pure_life_info_popups ||= new Set();
				if (!window.__pure_life_info_popups.has(id)) {
					window.__pure_life_info_popups.add(id);
					frappe.msgprint({ title: __("Information"), message: html, indicator: "orange" });
				}
			});
		});
	}
});
