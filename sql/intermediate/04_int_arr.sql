-- ARR at each month end.
-- Clean (reference): canonical customer, contract lines active on the last day of the month, migration gaps bridged.
-- Raw (what a naive query on the billing export returns): billing account, end dates as exported.
create or replace table int_arr_customer_month as
select m.month, c.customer_key, sum(c.annual_value_eur) as arr_eur
from int_months m
join int_contracts_clean c on c.start_date <= m.month_end and c.end_date_clean >= m.month_end
group by all;

create or replace table int_arr_account_month_raw as
select m.month, c.billing_account_id, sum(c.annual_value_eur) as arr_eur
from int_months m
join stg_billing_contracts c on c.start_date <= m.month_end and c.end_date >= m.month_end
group by all;
