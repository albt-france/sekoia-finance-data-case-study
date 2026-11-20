-- General ledger export (Pennylane-like, SIMULATED, simplified French chart of accounts). Owner: Head of Finance.
create or replace view stg_gl_entries as
select entry_id, cast(entry_date as date) as entry_date, cast(date_trunc('month', cast(entry_date as date)) as date) as month,
       journal, account, account_label,
       cast(debit_eur as double) as debit_eur, cast(credit_eur as double) as credit_eur,
       cast(debit_eur as double) - cast(credit_eur as double) as net_debit_eur,
       analytic_code, document_ref, label
from read_csv_auto('data/sim/gl_entries.csv', header = true, types = {'account': 'VARCHAR', 'analytic_code': 'VARCHAR'});
