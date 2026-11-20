-- The same month, three "ARR" figures: CRM (deals as typed), billing (contracts), ledger run-rate (subscription revenue x 12).
create or replace table fct_arr_three_values as
with gl as (
    select month, -sum(net_debit_eur) as saas_revenue_eur
    from int_gl_account_month where account = '706000' group by month
), raw as (
    select month, sum(arr_eur) as arr, count(*) as accounts from int_arr_account_month_raw group by month
), clean as (
    select month, sum(arr_eur) as arr, count(*) as customers from int_arr_customer_month group by month
)
select m.month,
       c.crm_arr_raw as arr_crm_as_typed,
       c.crm_arr_raw - c.tcv_effect - c.discount_effect - c.orphan_effect as arr_crm_corrected,
       raw.arr as arr_billing_raw,
       clean.arr as arr_billing_clean,
       gl.saas_revenue_eur * 12 as arr_gl_runrate,
       c.crm_customers as customers_crm,
       raw.accounts as customers_billing_raw,
       clean.customers as customers_clean
from int_months m
left join int_crm_arr_month c using (month)
left join raw using (month)
left join clean using (month)
left join gl using (month)
order by m.month;
