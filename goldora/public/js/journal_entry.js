// Client wants every new Journal Entry row to start blank.
// ERPNext auto-fills the difference in two places; both are neutralised here.

// 1. erpnext.accounts.JournalEntry.accounts_add (journal_entry.js:449) dumps
//    doc.difference into the new row.
//
//    This CANNOT be neutralised with frappe.ui.form.on("Journal Entry", {accounts_add}):
//    script_manager.trigger (frappe/public/js/frappe/form/script_manager.js:122-138)
//    queues new-style handlers BEFORE old-style controller methods, so core's
//    accounts_add always runs last and overwrites whatever we blank. Patch the
//    controller method itself instead.
if (
	typeof erpnext !== "undefined" &&
	erpnext.accounts &&
	erpnext.accounts.JournalEntry &&
	!erpnext.accounts.JournalEntry.prototype.__goldora_blank_rows
) {
	const proto = erpnext.accounts.JournalEntry.prototype;
	const core_accounts_add = proto.accounts_add;

	proto.accounts_add = function (doc, cdt, cdn) {
		// let core copy account/party/dimensions from the first row
		core_accounts_add.call(this, doc, cdt, cdn);

		const row = frappe.get_doc(cdt, cdn);
		row.debit = null;
		row.credit = null;
		row.debit_in_account_currency = null;
		row.credit_in_account_currency = null;

		// core computed the totals with the difference it just filled in
		this.frm.cscript.update_totals(doc);
		this.frm.refresh_field("accounts");
	};

	proto.__goldora_blank_rows = true;
}

// 2. called from set_account_details to re-fill the last row with the running difference
frappe.provide("erpnext.journal_entry");
erpnext.journal_entry.set_amount_on_last_row = function () {};
