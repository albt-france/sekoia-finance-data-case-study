-- Monthly cash position from the bank export, tied to the ledger bank account (512000). VAT flows are not simulated.
-- Operating cash flow excludes financing and the opening balance; runway uses the average of the last six months.
create or replace table fct_cash as
with t as (
    select m.month,
           sum(amount_eur) filter (where category = 'Customer receipts') as customer_receipts,
           sum(amount_eur) filter (where category like 'Payroll%') as payroll_paid,
           sum(amount_eur) filter (where category = 'Cloud providers') as cloud_paid,
           sum(amount_eur) filter (where category = 'Suppliers') as suppliers_paid,
           sum(amount_eur) filter (where category = 'Expense reimbursements') as expenses_paid,
           sum(amount_eur) filter (where category = 'Bank fees') as bank_fees,
           sum(amount_eur) filter (where category in ('Financing', 'Opening balance')) as financing_and_opening,
           sum(amount_eur) as net_movement
    from int_months m left join stg_cash_transactions c using (month) group by m.month
), gl as (
    select month, sum(net_debit_eur) as gl_movement from int_gl_account_month where account = '512000' group by month
), c as (
    select t.*, coalesce(gl.gl_movement, 0) as gl_movement,
           sum(net_movement) over (order by month) as closing_cash,
           sum(coalesce(gl.gl_movement, 0)) over (order by month) as gl_512_closing,
           net_movement - coalesce(financing_and_opening, 0) as operating_cash_flow
    from t left join gl using (month)
)
select month, closing_cash - net_movement as opening_cash, customer_receipts, payroll_paid, cloud_paid, suppliers_paid, expenses_paid,
       bank_fees, financing_and_opening, operating_cash_flow, closing_cash, gl_512_closing, closing_cash - gl_512_closing as bank_vs_gl_diff,
       avg(operating_cash_flow) over (order by month rows between 5 preceding and current row) as operating_cf_6m_avg,
       case when avg(operating_cash_flow) over (order by month rows between 5 preceding and current row) < 0
            then closing_cash / -avg(operating_cash_flow) over (order by month rows between 5 preceding and current row) end as runway_months
from c
order by month;
