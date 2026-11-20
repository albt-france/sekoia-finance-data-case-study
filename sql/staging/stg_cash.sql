-- Bank / treasury export (Agicap-like, SIMULATED). Owner: Head of Finance. VAT flows are left out of the simulation.
create or replace view stg_cash_transactions as
select cast(transaction_date as date) as transaction_date, cast(date_trunc('month', cast(transaction_date as date)) as date) as month,
       bank_account, cast(amount_eur as double) as amount_eur, category, counterparty, reference
from read_csv_auto('data/sim/cash_transactions.csv', header = true);
