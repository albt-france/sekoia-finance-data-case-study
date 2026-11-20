-- Ledger by month and account, with the P&L line of each account (simplified French chart of accounts).
create or replace table int_pnl_mapping as
select * from (values
    ('706000', 'Revenue', 'SaaS subscriptions'), ('706100', 'Revenue', 'Professional services'), ('709000', 'Revenue', 'Credit notes'),
    ('604100', 'COGS', 'Cloud hosting - AWS'), ('604200', 'COGS', 'Cloud hosting - Azure'), ('604300', 'COGS', 'Cloud hosting - OVHcloud'),
    ('604500', 'COGS', 'Threat-intel feeds and production tools'),
    ('641000', 'Payroll', 'Gross salaries'), ('641200', 'Payroll', 'Paid-leave accrual'), ('645000', 'Payroll', 'Employer contributions'),
    ('625100', 'Opex', 'Travel and expenses'), ('651000', 'Opex', 'Internal software'), ('623000', 'Opex', 'Marketing and events'),
    ('613200', 'Opex', 'Rent'), ('622600', 'Opex', 'Recruiting fees'), ('628000', 'Opex', 'Other G&A')
) t(account, pnl_group, pnl_line);

create or replace table int_gl_account_month as
select g.month, g.account, max(g.account_label) as account_label, g.journal, g.analytic_code,
       m.pnl_group, m.pnl_line, sum(g.net_debit_eur) as net_debit_eur
from stg_gl_entries g
left join int_pnl_mapping m using (account)
group by g.month, g.account, g.journal, g.analytic_code, m.pnl_group, m.pnl_line;
