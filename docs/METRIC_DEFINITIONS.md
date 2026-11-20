# Metric definitions: one number per question

> One definition per metric, its formula, the source that wins when systems disagree, and the traps.
> Figures quoted are from the SIMULATED company (fictional 180-person cybersecurity SaaS scale-up), November 2026.

## Revenue metrics

### ARR (Annual Recurring Revenue)
- **Definition**: annual value of the recurring subscription lines **active on the last day of the month**, from **signed contracts** in the billing system, on the canonical customer key.
- **Formula**: `sum(annual_value_eur)` of contract lines with `start_date <= month_end <= end_date_clean`.
- **Reference source**: billing contracts (`int_contracts_clean`). Not the CRM, not the ledger.
- **Includes**: platform subscription and recurring add-ons (SOAR, AI agents). **Excludes**: one-off onboarding services, credit notes, pipeline, signed deals not started yet.
- **Traps**: CRM deals typed at total contract value (TCV) on multi-year deals (+€6.2M in Nov 2026); end dates shifted by a tool migration (40 lines, March 2026); duplicate accounts; using `12 x monthly revenue` (lags and includes cut-off errors).
- Nov 2026: **€26.1M**, +24% year on year.

### MRR (Monthly Recurring Revenue)
- **Definition**: ARR / 12. Used for monthly views; never mixed with recognised revenue.

### Bookings
- **Definition**: annualised value of contracts **signed** in the period (closed-won in the CRM), split new / upsell / renewal.
- **Formula**: CRM amount, divided by `term / 12` when the deal is multi-year and the amount is the TCV.
- **Reference source**: CRM, checked line by line against billing (`crm_deal_id`). TCV is reported separately, never added to ARR.
- **Trap**: sales compensation is often paid on TCV; Finance reports annualised bookings.

### NRR (Net Revenue Retention), 12 months
- **Definition**: ARR today of the customers who already had ARR 12 months ago, divided by their ARR 12 months ago.
- **Formula**: `sum(ARR_m of base customers) / sum(ARR_m-12 of base customers)`; new customers are excluded; churned customers count for 0.
- **Reference source**: ARR above (canonical customer key).
- **Traps**: computed on billing accounts, a duplicate account turns a renewal into "churn + new logo" (NRR 104.6% instead of 108.3% in Nov 2026); computed on raw end dates, the March 2026 migration shows NRR at 91.0% instead of 108.2%.
- Nov 2026: **108.3%**.

### GRR (Gross Revenue Retention), 12 months
- **Definition**: same base as NRR, each customer capped at its ARR 12 months ago (expansion excluded). Cannot exceed 100%.
- Nov 2026: **96.4%**.

### Churn
- **Logo churn**: customers with ARR at m-1 and none at m, on the canonical key. **ARR churn**: their ARR at m-1.
- **Trap**: a renewal entered with a gap of a few days is not churn. Rule: a gap of 1 to 7 days between two lines of the same customer and product is bridged.

### Revenue (recognised)
- **Definition**: accounting revenue in the ledger: subscriptions spread evenly over the service period (706000), services when delivered (706100), credit notes (709000).
- **Reference source**: ledger (Pennylane-like). Checked monthly against invoices spread over their service periods (threshold 0.5%).
- **Trap**: invoices are billed upfront (annual) -> cash and revenue diverge; the difference sits in deferred revenue (487000).

## People metrics

| Metric | Definition | Nov 2026 | Source |
|---|---|---|---|
| HRIS active records | every active record at month end, interns and stale records included | 187 | HRIS |
| **Headcount (reported)** | employment contracts (CDI, CDD, apprentices) active on the last day of the month, **interns excluded**, records without a payslip excluded | **181** | HRIS status x payroll |
| FTE | sum of contractual working time of reported headcount (part-time 80% = 0.8) | 179.8 | HRIS |
| Paid persons | people with a payslip in the month (interns' stipend and leavers' final settlement included) | 187 | payroll |

- **Why three numbers are all "right"**: 4 interns (internship agreements, not employment contracts), 2 leavers whose HRIS end date was never entered, final settlements paid the month after a departure.
- **Payroll cost**: gross salaries + employer contributions from the payroll register (641000 + 645000), by department, aggregated. Central accruals (bonus, paid leave) are reconciled separately.
- **Confidentiality**: see `DATA_CONFIDENTIALITY.md` (no group under 5 people).

## Cost metrics

### COGS (cost of revenue)
- **Definition**: costs needed to deliver the service to current customers:
  1. **production hosting** (AWS, Azure, OVHcloud), in the month of service, non-production (staging) excluded;
  2. **AI inference** (model endpoints and GPU instances behind the AI agents feature);
  3. **support and SOC operations payroll** (department "SOC Operations & Support");
  4. **production tools** (threat-intel feeds and tools that run the service, 604500).
- **Excludes**: R&D and staging cloud, customer success, sales.
- **Traps**: taking the cloud bill in its booking month (cut-off); converting USD bills at the payment rate instead of the service-month rate; untagged resources left out.

### Gross margin
- **Formula**: `(revenue - COGS) / revenue`, revenue = recognised revenue (ledger).
- Nov 2026: **80.8%** (2026 average 80.1%). Listed security vendors, last 10-K: **70.3% to 78.1%** (PUBLIC DATA). Benchmarks, not targets: their COGS definitions differ.

### Cost per customer, unit economics
- Customer revenue = ARR / 12. Customer COGS = cost pools allocated by driver: storage and search by **stored GB**, ingestion by **GB ingested per day**, AI by **AI queries**, support by **segment weight**, shared platform and tools by **ARR**.
- **Retention cost**: storage + search cost of the logs kept; **~€34 per TB stored per month** in Nov 2026 at public list prices.

### Cloud cost change: price, volume, FX (AWS bill in USD)
- `EUR = list cost USD (volume) x (1 - discount) (price) / USD per EUR (FX)`;
- volume = `(L1 - L0) x (1 - d0) / r0`; price = `L1 x (d0 - d1) / r0`; FX = `L1 x (1 - d1) x (1/r1 - 1/r0)`; they add up exactly.

### Cash and expenses
- **Cash**: closing bank balance (all accounts), tied every month to ledger 512000.
- **Operating cash flow**: change in cash excluding financing; **runway** = cash / average monthly operating outflow (6 months), shown only when the company burns cash.
- **Expenses (opex)**: costs booked in the ledger by nature (travel, software, marketing, rent, recruiting, other G&A) in the month the expense report is approved. **Trap**: an event at the end of a month is booked the month after (accrue it at close if material).
