-- From the CRM figure to the billing figure, step by step (March 2026 = month of the migration, November 2026 = latest).
create or replace table fct_arr_waterfall as
with t as (
    select * from fct_arr_three_values where month in (date '2026-03-01', date '2026-11-01')
), c as (
    select * from int_crm_arr_month where month in (date '2026-03-01', date '2026-11-01')
)
select t.month, s.step_order, s.step, s.amount_eur
from t join c using (month),
lateral (values
    (1, 'CRM closed-won ARR, amounts as typed', t.arr_crm_as_typed),
    (2, 'Multi-year deals typed at total contract value', -c.tcv_effect),
    (3, 'CRM amount before the last discount', -c.discount_effect),
    (4, 'Closed-won deals with no billing contract', -c.orphan_effect),
    (5, 'Unexplained residual', t.arr_crm_as_typed - c.tcv_effect - c.discount_effect - c.orphan_effect - t.arr_billing_clean),
    (6, 'Billing ARR, contracts (clean) = reference', t.arr_billing_clean),
    (7, 'Contracts closed early by the billing migration (raw export only)', t.arr_billing_raw - t.arr_billing_clean),
    (8, 'Billing ARR, raw export', t.arr_billing_raw),
    (9, 'Ledger run-rate (subscription revenue x 12)', t.arr_gl_runrate)
) s(step_order, step, amount_eur)
order by t.month, s.step_order;
