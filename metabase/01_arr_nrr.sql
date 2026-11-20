-- Tab 1 - ARR & NRR. Reference: billing contracts (clean). SIMULATED data.

-- Q1.1 ARR bridge by month (stacked bar: new, expansion, contraction, churn; line: closing ARR)
select strftime(month, '%Y-%m') as month, new_arr, expansion_arr, contraction_arr, churned_arr, arr_close, customers
from fct_arr_monthly
where basis = 'contracts (clean)'
order by month;

-- Q1.2 ARR: reference vs raw billing export vs CRM vs ledger run-rate (line)
select strftime(month, '%Y-%m') as month, arr_billing_clean, arr_billing_raw, arr_crm_as_typed, arr_gl_runrate
from fct_arr_three_values
order by month;

-- Q1.3 NRR and GRR, trailing 12 months (line), clean vs raw
select strftime(month, '%Y-%m') as month, basis, round(nrr * 100, 1) as nrr_pct, round(grr * 100, 1) as grr_pct
from fct_nrr_cohort
where cohort = 'All'
order by basis, month;

-- Q1.4 NRR by cohort at the latest month (table)
select cohort, customers_base, round(arr_base) as arr_base, round(arr_now) as arr_now, round(nrr * 100, 1) as nrr_pct, round(grr * 100, 1) as grr_pct
from fct_nrr_cohort
where basis = 'contracts (clean)' and month = (select max(month) from fct_nrr_cohort)
order by cohort;
