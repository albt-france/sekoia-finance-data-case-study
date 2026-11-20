-- Contract lines in annual value, on the canonical customer key.
-- Rule: when the next line of the same customer and product starts 1 to 7 days after a line ends, the line is a
-- renewal and the gap is a data-entry artefact (March 2026 billing migration): the line is extended to the day before.
create or replace table int_contracts_clean as
with c as (
    select ct.*, x.customer_key
    from stg_billing_contracts ct
    join int_customer_xref x using (billing_account_id)
), n as (
    select *, lead(start_date) over (partition by customer_key, product order by start_date) as next_start
    from c
)
select *,
       coalesce(date_diff('day', end_date, next_start) between 2 and 8, false) as gap_bridged,
       case when date_diff('day', end_date, next_start) between 2 and 8 then cast(next_start - interval 1 day as date)
            else end_date end as end_date_clean,
       annual_value_eur / 12 as mrr_eur
from n;

create or replace table int_customer_cohort as
select customer_key, min(start_date) as first_start, cast(year(min(start_date)) as varchar) as cohort
from int_contracts_clean
group by customer_key;
