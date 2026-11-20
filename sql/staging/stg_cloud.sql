-- AWS, Azure and OVHcloud bills in FOCUS v1.4 column names (SIMULATED usage x REAL public unit prices). Owner: FinOps Manager.
create or replace view stg_cloud_costs_focus as
select cast(ChargePeriodStart as date) as month, ServiceProviderName as provider, ServiceName as service_name,
       ServiceCategory as service_category, RegionId as region_id, ResourceId as resource_id, ResourceType as resource_type,
       SkuId as sku_id, cast(ConsumedQuantity as double) as consumed_quantity, ConsumedUnit as consumed_unit,
       cast(ListUnitPrice as double) as list_unit_price, cast(ListCost as double) as list_cost,
       cast(EffectiveCost as double) as effective_cost, cast(BilledCost as double) as billed_cost,
       BillingCurrency as billing_currency, InvoiceId as invoice_id, Tags as tags
from read_csv_auto('data/sim/cloud_costs_focus.csv', header = true);
