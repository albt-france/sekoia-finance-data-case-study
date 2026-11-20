-- PUBLIC DATA: ECB USD/EUR monthly averages, French public holidays (Nager.Date), SEC 10-K benchmarks.
create or replace view stg_fx_usd_eur as
select cast(month || '-01' as date) as month, cast(usd_per_eur as double) as usd_per_eur
from read_csv_auto('data/public/ecb_usd_eur_monthly.csv', header = true, types = {'month': 'VARCHAR'});

create or replace view stg_fr_holidays as
select cast(date as date) as holiday_date, name from read_csv_auto('data/public/fr_public_holidays.csv', header = true);

create or replace view stg_sec_benchmarks as
select * from read_csv_auto('data/public/sec_benchmarks.csv', header = true);
