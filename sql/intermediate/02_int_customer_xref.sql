-- One customer, one key. Billing accounts are grouped on the VAT number (legal identity), the CRM id is carried over
-- to every account of the group, and the normalised name is kept as a second check.
-- customer_key = C + the lowest account number of the group, so the key is stable when a duplicate is created.
create or replace table int_customer_xref as
with a as (
    select *,
           cast(substr(billing_account_id, 5) as integer) as account_no,
           trim(regexp_replace(regexp_replace(regexp_replace(lower(account_name), '[^a-z0-9 ]', '', 'g'),
                '\b(sas|sa|gmbh|sl|spa|bv|ltd)\b', '', 'g'), '\s+', ' ', 'g')) as name_key
    from stg_billing_accounts
)
select billing_account_id, account_name, vat_number, name_key,
       crm_company_id as crm_company_id_on_account,
       max(crm_company_id) over (partition by vat_number) as crm_company_id,
       'C' || lpad(cast(min(account_no) over (partition by vat_number) - 999 as varchar), 4, '0') as customer_key,
       count(*) over (partition by vat_number) as accounts_with_same_vat,
       min(name_key) over (partition by vat_number) = max(name_key) over (partition by vat_number) as names_agree,
       case when count(*) over (partition by vat_number) > 1 then 'duplicate account merged on VAT number'
            else 'single account' end as match_method
from a;

create or replace table int_customer_master as
select x.customer_key, max(x.crm_company_id) as crm_company_id, max(c.company_name) as customer_name,
       max(c.segment) as segment, max(c.country) as country, count(*) as billing_accounts
from int_customer_xref x
left join stg_crm_companies c on c.crm_company_id = x.crm_company_id
group by x.customer_key;
