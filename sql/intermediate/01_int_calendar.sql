-- Month spine (Dec 2024 - Nov 2026) and the USD/EUR rate of each month.
-- The ECB monthly average for the current month is published after month end: the last known rate is carried forward (ASOF join).
create or replace table int_months as
select cast(m as date) as month, cast(last_day(m) as date) as month_end
from range(timestamp '2024-12-01', timestamp '2026-12-01', interval 1 month) t(m);

create or replace table int_fx_monthly as
select m.month, f.usd_per_eur, f.month as fx_source_month, f.month <> m.month as fx_carried_forward
from int_months m asof left join stg_fx_usd_eur f on m.month >= f.month;

-- Close calendar: working day D+1 ... D+5 after each month end (weekends and French public holidays excluded)
create or replace table int_close_calendar as
with d as (
    select m.month, cast(m.month_end + interval (i) day as date) as day
    from int_months m, range(1, 15) r(i)
), w as (
    select d.*, row_number() over (partition by month order by day) as working_day
    from d
    where dayofweek(day) not in (0, 6) and day not in (select holiday_date from stg_fr_holidays)
)
select month, working_day, day from w where working_day <= 5;
