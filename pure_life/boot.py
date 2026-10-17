import frappe


def boot_session(bootinfo):
	bootinfo.pure_life_fleet_features = bool(frappe.conf.get("pure_life_fleet_features"))
