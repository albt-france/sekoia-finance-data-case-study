# Reconciliations: rule, threshold, latest result

> Every check runs each month in `sql/marts/19_fct_reconciliations.sql` (24 months, Dec 2024 - Nov 2026, SIMULATED data)
> and is tested by `python src/run_tests.py`. Status: **OK** (within threshold), **EXPLAINED** (documented items bring the
> residual within threshold), **WARN** (cash difference under threshold but not zero), **KO** (investigate before publishing).

## How I work a difference (the method behind every check)
1. **Same scope?** Same date (month end), same perimeter (recurring only), same currency, same customer key.
2. **Size it** as a cascade from source A to source B, largest effect first.
3. **Classify** each piece: definition (e.g. TCV vs annual), timing (cut-off), data entry (duplicate, missing end date), real gap.
4. **Fix at source** with the owner (role) and add a test, so the same gap cannot come back silently.
5. **Publish** only the reference number, with the open items listed.

## Checks

| # | Check | Source A | Source B | Rule | Threshold | Latest result (Nov 2026) | 24-month record |
|---|---|---|---|---|---|---|---|
| 1 | CRM vs billing ARR | CRM closed-won deals, amount as typed | billing contracts (clean) | deal <-> contract line on `crm_deal_id`; differences classified (TCV, discount, no contract) | residual < 1% | CRM **€32.6M** vs billing **€26.1M** (+24.7%); explained: TCV €6.25M, discount €0.11M, 4 deals with no contract €0.10M; residual **€0** | 24 EXPLAINED |
| 2 | Billing vs ledger subscription revenue | invoices spread over their service period | ledger 706000 | monthly; timing rule | 0.5% | OK | 22 OK, 2 EXPLAINED (June/July 2026: 3 invoices recognised a month late, €13.3k) |
| 3 | Payroll register vs ledger payroll cost | payroll register (gross + employer contributions) | ledger 641000 + 645000 | monthly, total and by department | 0.5% | OK | 22 OK, 2 EXPLAINED (year-end bonus accrual €475k in Dec 2025, reversed in Mar 2026) |
| 4 | Cloud bills vs ledger hosting | FOCUS exports in EUR (service month) | ledger 604100-604300 | invoice id = document ref; timing rule | 0.5% | OK | 22 OK, 2 EXPLAINED (Azure bill of May 2026 booked in June, €10.5k) |
| 5 | Bank vs ledger cash | bank export closing balance | ledger 512000 | monthly balance | 0.01% of balance | **WARN**: -€1,840 | 22 OK, 2 WARN (bank fee of Oct 2026 not booked) |
| 6 | HRIS vs payroll headcount | HRIS active records (interns excluded) | people with a regular payslip | employee id, month end | 0 | EXPLAINED: 2 records | 18 OK, 6 EXPLAINED (2 leavers without HRIS end date since June 2026) |
| 7 | ARR: billing raw vs contracts clean | billing export as is | contracts with gaps bridged | gap of 1-7 days between lines of the same customer and product | n/a (diagnostic) | equal | March 2026: raw **€19.9M** vs clean **€22.4M**: 40 renewal lines closed one day early by the billing migration |

## Cascades (largest first)

**CRM -> billing ARR, November 2026**

| Step | EUR |
|---|---|
| CRM closed-won ARR, amounts as typed | 32,572,900 |
| - multi-year deals typed at total contract value (53 deals) | -6,247,183 |
| - CRM amount before the last discount | -109,317 |
| - closed-won deals with no billing contract (4) | -96,000 |
| = billing ARR, contracts (clean) | **26,120,400** |
| residual | 0 |

**Billing raw -> clean, March 2026 (the false signal)**: raw export €19.89M; + 40 renewal lines whose old line ends on 30 March and the new one starts on 1 April: +€2.49M; = €22.38M. The ledger run-rate (subscription revenue x 12) is €22.38M too: **nothing was lost; no alert to management.**

## Open items and owners
| Item | Owner (role) | Action |
|---|---|---|
| 53 multi-year deals with TCV in the amount field | RevOps Manager | add an "annual value" property, make it mandatory at closed-won |
| 4 closed-won deals with no billing contract | RevOps Manager + billing ops | create the contracts or reopen the deals |
| 12 duplicate billing accounts | billing ops | merge, make VAT number unique in billing |
| 2 HRIS records still active | People team | enter the end dates |
| bank fee Oct 2026 | Head of Finance | book it at the November close |
