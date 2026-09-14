# Detailed inter-company counterpart JE

## Context
`book()` in `goldora/intercompany.py` adds up every inter-company row into a single net amount and posts it as one party row plus one suspense row. For ACC-JV-2026-00266-1, the source had 1310/Customer عبير Dr 20,000 ("مكتب ركاز عبير المستقبل") and Cr 300,000 ("تحويل من عبير المستقبل"). The counterpart ACC-JV-2026-00282 came out as one 280,000 line. The client wants the detail: one counterpart line per source line, with each line's remark kept.

## Accounting decisions (recommended defaults; the client's accountant should confirm)
1. **Both party rows go on one account and one party**, chosen by the net, exactly as today (net < 0 gives Receivable/Customer; net > 0 gives Payable/Supplier).
   - The source keeps both lines on a single account (1310) for عبير, so the mirror should also keep غولدورا on a single balance.
   - The two companies' balances then still cancel on consolidation, and their statements can be matched line by line.
   - Picking Customer or Supplier per line would split one counterparty into a receivable and a payable. The GL total would be the same, but reconciliation and party statements would be messier.
   - The party balance ends up the same as today (Dr 280,000 net). Only the presentation changes.
2. **Each party row gets its own suspense (1910) row.** The counterpart is a draft, and the target company's accountant replaces the suspense rows with real accounts. With one suspense row per line, the 300k transfer can go to the bank and the 20k to its own account. The 1910 total is the same as the net version.
3. **Copy each source row's `user_remark`** onto both of its counterpart rows. This has no accounting effect.
4. **Net zero still skips** (current behavior is unchanged).

**Visible side effect:** the counterpart's `total_debit`/`total_amount` becomes the gross amount (320,000) instead of the net (280,000). Party and GL balances do not change.

Resulting counterpart for this example (company عبير, draft):
| Account | Party | Dr | Cr | Remark |
|---|---|---|---|---|
| 1310 مدينون | Customer غولدورا | 300,000 | | تحويل من عبير المستقبل |
| 1910 افتتاحي مؤقت | | | 300,000 | تحويل من عبير المستقبل |
| 1310 مدينون | Customer غولدورا | | 20,000 | مكتب ركاز عبير المستقبل |
| 1910 افتتاحي مؤقت | | 20,000 | | مكتب ركاز عبير المستقبل |

## Change (single file: `goldora/intercompany.py`)
- Split the grouping out of `_net_by_company`: a `_rows_by_company(doc)` helper returns `{company: [rows]}`, and `_net_by_company` keeps its signature by summing over it. `validate()` stays unchanged.
- In `book()`, keep everything up to choosing `party_type`, `account`, and `party` from the net. Then replace the two hard-coded `je.append` branches with a loop over that company's rows:
  - `amt = flt(r.debit_in_account_currency - r.credit_in_account_currency, precision)`; skip if 0.
  - Source Dr (amt > 0): party row Cr `amt`, suspense row Dr `amt`.
  - Source Cr (amt < 0): party row Dr `-amt`, suspense row Cr `-amt`.
  - Both rows use `cost_center` and `user_remark=r.user_remark`.
- `_check_target_company` still runs once per company on the net party type, so the readiness checks are unchanged.

## Tests (`goldora/tests/test_intercompany.py`)
- Add `test_counterpart_is_detailed_per_row`: the source has a Customer row Dr 20 and a Customer row Cr 300 (both with remarks), balanced by a bank row. Assert:
  - The counterpart has 4 rows.
  - Both party rows are on `receivable_b`: one Dr 300 and one Cr 20.
  - The suspense rows are Cr 300 and Dr 20.
  - Remarks are copied.
  - The party row net is Dr 280.
- The existing single-row tests (happy path, cancel, recursion) must still pass unchanged.

## Verification
- `bench --site <site> run-tests --app goldora --module goldora.tests.test_intercompany`
- Submit a test JE shaped like 00266-1 on the dev site and inspect the draft counterpart.

## Existing data (only with explicit OK)
ACC-JV-2026-00282 is still a draft with the net layout. After deploying, it can be regenerated: delete the draft, clear the link on 00266-1, then call `goldora.intercompany.book(frappe.get_doc("Journal Entry", "ACC-JV-2026-00266-1"))` in the bench console. None of this is done without confirmation.
