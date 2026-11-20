-- Travel and expense export (Navan-like, SIMULATED). Owner: Head of Finance.
create or replace view stg_expenses as
select expense_id, employee_id, cast(expense_date as date) as expense_date, cast(submitted_date as date) as submitted_date,
       cast(approved_date as date) as approved_date, category, cast(amount_eur as double) as amount_eur, trip_tag
from read_csv_auto('data/sim/expenses.csv', header = true);
