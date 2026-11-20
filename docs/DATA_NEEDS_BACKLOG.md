# Finance data needs: prioritised backlog

> Scoring: **value** (1-5: decisions it unlocks, risk it removes), **effort** (1-5), **dependency on Data Engineering**
> (none / low / high). Priority = value / effort, then fewer dependencies first. SIMULATED context.

| Rank | Need | Why (decision or risk) | Value | Effort | Data Eng. | Owner (role) |
|---|---|---|---|---|---|---|
| 1 | One customer key across CRM, billing and usage (VAT number unique in billing, CRM id mandatory) | NRR and customer count are wrong by 3.7 pts / 12 accounts today | 5 | 2 | low | billing ops, RevOps Manager |
| 2 | Annual value field in the CRM, mandatory at closed-won; TCV kept separately | CRM ARR overstated by 25%; bookings and commissions disputes | 5 | 1 | none | RevOps Manager |
| 3 | ARR, NRR, GRR from billing contracts in Metabase, with the gap rule and tests | one ARR for board, investors and sales | 5 | 2 | low | Finance Data Analyst |
| 4 | Monthly reconciliation pack (6 checks) run automatically at D+2, results in Metabase | close faster, fewer surprises | 4 | 2 | low | Finance Data Analyst |
| 5 | Tagging policy enforced at deploy (product, env, customer tier) + allocation rule for the rest | AI and product margins unmeasurable (18% of resources untagged) | 4 | 3 | high | FinOps Manager, Data Engineering |
| 6 | Cost to serve per customer (stored TB, ingestion, AI queries) refreshed monthly | 3 customers below zero margin went unnoticed for 16 months | 5 | 3 | high | Finance Data Analyst, Data Engineering |
| 7 | Retention and ingestion above contract flagged to sales before renewal | reprice the 3 loss-making accounts; stop new ones | 4 | 2 | low | Head of Finance |
| 8 | Budget in Pigment with explicit drivers (USD rate, AWS discount, volume) | price / volume / FX variance in one click | 4 | 2 | none | Finance Data Analyst |
| 9 | Headcount definitions in HRIS reports (interns, apprentices, FTE) + HRIS / payroll check | three headcounts in three decks | 3 | 1 | none | People team |
| 10 | Accrual list for known events at close (travel, cloud, bonus) | monthly variance commentary that holds | 3 | 1 | none | Head of Finance |
| 11 | Cash forecast in Agicap fed by billing (invoice schedule) and payroll | runway based on contracts, not on averages | 3 | 3 | low | Head of Finance |
| 12 | Usage and cost data ready for anomaly detection (daily FOCUS, daily usage) | catch cost spikes in days, not at month end | 3 | 4 | high | Data Engineering, FinOps Manager |
