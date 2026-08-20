// Client wants every new Journal Entry row to start blank.
// ERPNext auto-fills the difference in two places; both are neutralised here.

frappe.ui.form.on("Journal Entry", {
	// runs after the core accounts_add, so it wipes what core just filled in
	accounts_add: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.debit = null;
		row.credit = null;
		row.debit_in_account_currency = null;
		row.credit_in_account_currency = null;
		frm.refresh_field("accounts");
	},
});

frappe.provide("erpnext.journal_entry");
// called from set_account_details to re-fill the last row with the running difference
erpnext.journal_entry.set_amount_on_last_row = function () {};
