-- Data tests. Each block starts with "-- test: <name>" and returns the FAILING rows: zero rows = OK.
-- Run with: python src/run_tests.py

-- test: unique contract_id in billing
select contract_id, count(*) from stg_billing_contracts group by 1 having count(*) > 1;

-- test: unique invoice_id in billing
select invoice_id, count(*) from stg_billing_invoices group by 1 having count(*) > 1;

-- test: unique deal_id in CRM
select deal_id, count(*) from stg_crm_deals group by 1 having count(*) > 1;

-- test: unique employee_id in HRIS
select employee_id, count(*) from stg_hris_employees group by 1 having count(*) > 1;

-- test: one payslip per person, month and type
select month, employee_id, payslip_type, count(*) from stg_payroll_monthly group by all having count(*) > 1;

-- test: no null keys or amounts in billing, ledger and payroll
select 'contract' as t, contract_id from stg_billing_contracts where billing_account_id is null or annual_value_eur is null or start_date is null
union all select 'invoice', invoice_id from stg_billing_invoices where amount_excl_tax_eur is null or invoice_date is null
union all select 'gl', entry_id from stg_gl_entries where account is null or entry_date is null
union all select 'payroll', employee_id from stg_payroll_monthly where gross_eur is null;

-- test: every ledger entry is balanced (debit = credit)
select entry_id, sum(debit_eur) - sum(credit_eur) as gap from stg_gl_entries group by 1 having abs(sum(debit_eur) - sum(credit_eur)) > 0.01;

-- test: every billing account maps to one canonical customer
select billing_account_id from stg_billing_accounts where billing_account_id not in (select billing_account_id from int_customer_xref)
union all select billing_account_id from int_customer_xref group by 1 having count(distinct customer_key) > 1;

-- test: merged duplicate accounts have the same normalised name
select billing_account_id, account_name from int_customer_xref where accounts_with_same_vat > 1 and not names_agree;

-- test: ARR bridge adds up (open + new + expansion + contraction + churn = close)
select month, basis from fct_arr_monthly
where abs(arr_open + new_arr + expansion_arr + contraction_arr + churned_arr - arr_close) > 1;

-- test: reference ARR never falls by more than 3% in a month (catches data artefacts such as migration gaps)
select month, arr_close, arr_open from fct_arr_monthly
where basis = 'contracts (clean)' and arr_close / arr_open - 1 < -0.03;

-- test: NRR and GRR within plausible bounds (GRR <= 100% <= ... and NRR >= GRR)
select month, cohort from fct_nrr_cohort where basis = 'contracts (clean)' and (grr > 1 or nrr < grr or nrr > 1.6 or grr < 0.5);

-- test: unit-economics allocation is complete (allocated COGS = COGS pools, per month)
select p.month, p.pools, u.allocated from (select month, sum(amount_eur) as pools from int_cogs_pools group by 1) p
join (select month, sum(cogs_eur) as allocated from fct_unit_economics group by 1) u using (month)
where abs(p.pools - u.allocated) > 1;

-- test: reconciliation CRM vs billing ARR: residual below 1% after classified differences
select month, residual from fct_reconciliations where check_name = 'CRM vs billing ARR' and status = 'KO';

-- test: reconciliation billing vs ledger revenue: residual below 0.5%
select month, residual from fct_reconciliations where check_name = 'Billing vs ledger subscription revenue' and status = 'KO';

-- test: reconciliation payroll vs ledger: residual below 0.5%
select month, residual from fct_reconciliations where check_name = 'Payroll register vs ledger payroll cost' and status = 'KO';

-- test: reconciliation cloud bills vs ledger: residual below 0.5%
select month, residual from fct_reconciliations where check_name = 'Cloud bills vs ledger hosting' and status = 'KO';

-- test: reconciliation bank vs ledger cash: difference below 0.01% of the balance
select month, residual from fct_reconciliations where check_name = 'Bank vs ledger cash' and status = 'KO';

-- test: everyone in reported headcount has a regular payslip that month
select month, employee_id from int_employee_month
where hris_active_month_end and contract_type <> 'Intern' and not suspected_leaver and not has_regular_payslip and month <> date '2024-12-01';

-- test: confidentiality - no payroll figure for a group of fewer than 5 people
select month, department from fct_headcount_payroll where paid_persons < 5 and payroll_cost_eur is not null;

-- test: confidentiality - no person-level column in any exported mart
select table_name, column_name from information_schema.columns
where table_name like 'fct_%' and regexp_matches(lower(column_name), '^(employee|person)|salary|first_name|last_name|email');

-- test: budget covers every month and line of 2026 to date
select budget_line, count(*) from fct_budget_vs_actual group by 1 having count(*) <> 11;

-- test: price + volume + FX effects add up to the AWS change
select month, comparison from fct_cloud_price_volume_fx
where abs(volume_effect_eur + price_effect_eur + fx_effect_eur - change_eur) > 1;
