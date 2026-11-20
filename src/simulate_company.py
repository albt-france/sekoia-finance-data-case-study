"""Simulate 24 months (Dec 2024 - Nov 2026) of Finance data for a FICTIONAL 180-person cybersecurity SaaS scale-up.

SIMULATED: these are not Sekoia's numbers. Each export is *inspired by* the columns of common tools (CRM, billing,
accounting, cash, planning, HRIS, payroll, expenses, ATS, AWS / Azure / OVH bills); none is presented as a real schema.
Real public inputs: cloud unit prices (AWS, Azure, OVHcloud), ECB USD/EUR rates, French public holidays.
Eight data problems are planted on purpose; their truth goes to data/_hidden_truth.csv (kept out of the repository).
    python src/simulate_company.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUB, SIM = ROOT / "data" / "public", ROOT / "data" / "sim"
SIM.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42)

MONTHS = pd.period_range("2024-12", "2026-11", freq="M")
M_START = {m: m.to_timestamp() for m in MONTHS}
M_END = {m: m.to_timestamp(how="end").normalize() for m in MONTHS}
AI_LAUNCH = pd.Period("2025-10", "M")
MIGRATION = pd.Timestamp("2026-03-31")          # billing tool cut-over (event 1)
SKO = pd.Period("2026-01", "M")                  # sales kick-off trip (event 8)
TRUTH = []


def truth(event, what, value, ids=""):
    TRUTH.append({"event": event, "what": what, "value": value, "ids": ids})


# ------------------------------------------------------------------ public inputs
fx = pd.read_csv(PUB / "ecb_usd_eur_monthly.csv")
FX = {pd.Period(r.month, "M"): r.usd_per_eur for r in fx.itertuples()}
for m in MONTHS:                                  # Nov 2026 not yet published by the ECB: carry October forward
    if m not in FX:
        FX[m] = FX[max(k for k in FX if k < m)]
P = pd.read_csv(PUB / "cloud_unit_prices.csv")


def price(provider, service_like, sku_like):
    r = P[(P.provider == provider) & P.service.str.contains(service_like, regex=False) & P.sku.str.contains(sku_like, regex=False)]
    return float(r.price.iloc[0])


PR = {"s3_std": price("AWS", "S3", "Standard"), "s3_ia": price("AWS", "S3", "Infrequent"),
      "r6i": price("AWS", "EC2", "r6i.2xlarge"), "m6i": price("AWS", "EC2", "m6i.xlarge"),
      "c6i": price("AWS", "EC2", "c6i.2xlarge"), "g5": price("AWS", "EC2", "g5.xlarge"),
      "az_hot": price("Azure", "Blob", "Hot"), "az_cool": price("Azure", "Blob", "Cool"),
      "ovh_obj": price("OVHcloud", "Public Cloud", "Object Storage"), "ovh_b316": price("OVHcloud", "Public Cloud", "b3-16"),
      "ovh_tok": price("OVHcloud", "AI Endpoints", "input")}
HOURS = {m: m.days_in_month * 24 for m in MONTHS}

# ------------------------------------------------------------------ customers (canonical truth)
SYL1 = ["Nor", "Var", "Lu", "Te", "Bri", "Cal", "Zen", "Or", "Mi", "Sa", "Del", "Ka", "Ri", "Ves", "Tal", "Pol", "Arv", "Eko", "Qui", "Hel"]
SYL2 = ["vexa", "ra", "mo", "tis", "vo", "nix", "lia", "dor", "ven", "tro", "ane", "sio", "bel", "quar", "ton"]
SECTOR = ["Logistics", "Energie", "Sante", "Bank", "Industries", "Retail", "Telecom", "Assurances", "Group", "Systems", "Mutuelle", "Transports"]
LEGAL = {"FR": "SAS", "BE": "SA", "DE": "GmbH", "ES": "SL", "IT": "SpA", "NL": "BV", "UK": "Ltd"}
SEG = {"SMB": (0.45, 6, 1800, 9000), "Mid-market": (0.35, 30, 1100, 20000), "Enterprise": (0.12, 140, 800, 60000), "MSSP": (0.08, 260, 550, 80000)}
CHURN_AT_RENEWAL = {"SMB": 0.08, "Mid-market": 0.05, "Enterprise": 0.025, "MSSP": 0.03}

names, cust = set(), []


def new_customer(i, start):
    seg = rng.choice(list(SEG), p=[v[0] for v in SEG.values()])
    country = rng.choice(list(LEGAL), p=[0.68, 0.08, 0.07, 0.05, 0.04, 0.04, 0.04])
    while True:
        n = f"{rng.choice(SYL1)}{rng.choice(SYL2)} {rng.choice(SECTOR)}"
        if n not in names:
            names.add(n)
            break
    _, ing, p_gb, floor = SEG[seg]
    ingest = float(np.clip(rng.lognormal(np.log(ing), 0.5), ing * 0.25, ing * 4))
    plan = "Flat" if rng.random() < {"SMB": 0.15, "Mid-market": 0.25, "Enterprise": 0.45, "MSSP": 0.5}[seg] else "Usage"
    term = int(rng.choice([12, 24, 36], p=[0.8, 0.1, 0.1]) if seg in ("Enterprise", "MSSP", "Mid-market") else 12)
    return {"customer_id": f"C{i:04d}", "name": f"{n} {LEGAL[country]}", "segment": seg, "country": country, "plan": plan,
            "ingest0": ingest, "price_gb": p_gb * rng.uniform(0.9, 1.1), "floor": floor, "first_start": start, "term": term,
            "retention": int(rng.choice([90, 180, 365], p=[0.75, 0.18, 0.07])),
            "vat": f"{country}{rng.integers(10**9, 10**10)}", "domain": n.split()[0].lower() + rng.choice([".fr", ".com", ".eu", ".io"]),
            "public_sector": rng.random() < (0.12 if country == "FR" else 0.02), "azure_region": rng.random() < 0.08,
            "ai_adopter": rng.random() < 0.55, "growth": rng.normal(0.16, 0.12)}


# initial base: start months between 2022-06 and 2024-12, heavy in April (fiscal-year renewals)
start_pool = pd.period_range("2022-06", "2024-12", freq="M")
w = np.array([3.0 if p.month == 4 else 1.0 for p in start_pool]) * np.linspace(0.6, 1.4, len(start_pool))
i = 0
for _ in range(285):
    i += 1
    cust.append(new_customer(i, rng.choice(start_pool, p=w / w.sum()).to_timestamp()))
for m in MONTHS[1:]:
    for _ in range(rng.poisson(10 if m.month == 4 else 6.8)):
        i += 1
        cust.append(new_customer(i, M_START[m]))
C = pd.DataFrame(cust)

# event 6: three large flat-fee customers extend retention without repricing
big_flat = C[(C.plan == "Flat") & (C.segment == "Enterprise") & (C.first_start < "2024-06-01")].nlargest(3, "ingest0")
C.loc[big_flat.index, "retention"] = 120
C.loc[big_flat.index, "ingest0"] = C.loc[big_flat.index, "ingest0"].clip(lower=600)
C.loc[big_flat.index, "price_gb"] = 140.0          # large flat deals signed at a deep volume discount
C.loc[big_flat.index, "floor"] = 0
RET_EXT = pd.Period("2025-07", "M")
truth(6, "flat-fee customers whose log retention goes 120 -> 365 days in 2025-07 (no repricing)", 3, ",".join(big_flat.customer_id))


def ingest_at(c, d):
    years = max((d - c["first_start"]).days / 365.25, 0)
    return c["ingest0"] * (1 + c["growth"]) ** years


def contract_value(c, d):
    if c["plan"] == "Flat" and d > c["first_start"]:
        return None                                         # flat fee: price only revised by the growth factor below
    return max(c["floor"], ingest_at(c, d) * c["price_gb"]) * {90: 1.0, 180: 1.12, 365: 1.3}[c["retention"] if c["retention"] in (90, 180, 365) else 90]


# ------------------------------------------------------------------ contracts (truth), renewals, churn, upsells
SIM_END = pd.Timestamp("2026-11-30")
lines = []
k = 0
for c in C.to_dict("records"):
    start, value, renewal_no, addons = c["first_start"], contract_value(c, c["first_start"]), 0, 0.0
    while start <= SIM_END:
        term = c["term"] if renewal_no == 0 else (12 if c["term"] == 12 else int(rng.choice([12, c["term"]])))
        end = (pd.Period(start, "M") + term - 1).to_timestamp(how="end").normalize()
        k += 1
        lines.append({"line_id": k, "customer_id": c["customer_id"], "product": "SOC platform", "start": start, "end": end,
                      "term": term, "acv": round(value, -2), "kind": "new" if renewal_no == 0 else "renewal"})
        # mid-term add-on (SOAR or AI agents after launch), co-terminating
        if rng.random() < 0.18 and term >= 12:
            up_start = (pd.Period(start, "M") + int(rng.integers(3, 10))).to_timestamp()
            if up_start <= min(end, SIM_END):
                prod = "AI agents add-on" if pd.Period(up_start, "M") >= AI_LAUNCH and rng.random() < 0.6 else "SOAR add-on"
                k += 1
                up = round(value * rng.uniform(0.08, 0.2), -2)
                addons += up
                lines.append({"line_id": k, "customer_id": c["customer_id"], "product": prod, "start": up_start, "end": end,
                              "term": (pd.Period(end, "M") - pd.Period(up_start, "M")).n + 1, "acv": up, "kind": "upsell"})
        nxt = end + pd.Timedelta(days=1)
        if nxt > SIM_END:
            break
        if rng.random() < CHURN_AT_RENEWAL[c["segment"]]:
            C.loc[C.customer_id == c["customer_id"], "churn_date"] = nxt
            break
        renewal_no += 1
        if c["plan"] == "Flat":
            value = value * rng.uniform(1.0, 1.06)
        else:
            value = contract_value(c, nxt) * (rng.uniform(0.75, 0.9) if rng.random() < 0.08 else 1.0)
        value, addons = value + addons, 0.0          # add-ons are folded into the renewed platform line
        start = nxt
L = pd.DataFrame(lines)
L = L[L.start <= SIM_END].reset_index(drop=True)

# ------------------------------------------------------------------ billing system (Younium-like export)
C["billing_account_id"] = [f"ACC-{1000 + j}" for j in range(len(C))]
C["crm_company_id"] = [f"HS{560000 + j * 7}" for j in range(len(C))]
acc = C[["billing_account_id", "name", "vat", "country", "crm_company_id", "customer_id"]].copy()
acc["created_in"] = "billing_v1"
L["billing_account_id"] = L.customer_id.map(C.set_index("customer_id").billing_account_id)

# event 2: 12 duplicate billing accounts created at a renewal (name typed again, no CRM link, same VAT number)
ren = L[(L.kind == "renewal") & (L.start >= "2025-06-01") & (L.start <= "2026-09-01")]
dup_c = rng.choice(ren.customer_id.unique(), 12, replace=False)
dups = []
for j, cid in enumerate(dup_c):
    row = acc[acc.customer_id == cid].iloc[0]
    new_id = f"ACC-{5000 + j}"
    variant = row["name"].upper().replace(" SAS", " S.A.S.").replace(" SA", " S.A.").replace(" GMBH", " GmbH")
    dups.append({"billing_account_id": new_id, "name": variant, "vat": row.vat, "country": row.country, "crm_company_id": None,
                 "customer_id": cid, "created_in": "billing_v1"})
    first_ren = ren[ren.customer_id == cid].start.min()
    L.loc[(L.customer_id == cid) & (L.start >= first_ren), "billing_account_id"] = new_id
acc = pd.concat([acc, pd.DataFrame(dups)], ignore_index=True)
truth(2, "duplicate billing accounts (same VAT number, name typed again, no CRM id)", 12, ",".join(dup_c))

# event 1: migration leaves a one-day gap on 40 renewals (old line closed on 30 March instead of 31 March)
L["billing_end"] = L.end
L["source_system"] = np.where(L.start >= "2026-04-01", "billing_v2", "billing_v1")
cands = L[(L.end == MIGRATION) & (L["product"] == "SOC platform") & (L.customer_id.isin(L[(L.start == MIGRATION + pd.Timedelta(days=1)) & (L["product"] == "SOC platform")].customer_id))]
gap_ids = rng.choice(cands.line_id.values, min(40, len(cands)), replace=False)
L.loc[L.line_id.isin(gap_ids), "billing_end"] = MIGRATION - pd.Timedelta(days=1)
truth(1, "renewal lines closed one day early by the March 2026 billing migration (nothing lost)", len(gap_ids), "")
assert len(gap_ids) == 40, len(gap_ids)

L["contract_id"] = [f"K{n:05d}" for n in L.line_id]
L["billing_frequency"] = np.where(rng.random(len(L)) < 0.8, "annual", "quarterly")
cmap = C.set_index("customer_id")
contracts = pd.DataFrame({
    "contract_id": L.contract_id, "billing_account_id": L.billing_account_id, "crm_deal_id": [f"D{n:06d}" for n in L.line_id], "product": L["product"],
    "start_date": L.start.dt.date, "end_date": L.billing_end.dt.date, "term_months": L.term,
    "annual_value_eur": L.acv, "billing_frequency": L.billing_frequency,
    "plan_type": L.customer_id.map(cmap.plan), "committed_ingest_gb_day": L.customer_id.map(cmap.ingest0).round(0),
    "retention_days": L.customer_id.map(cmap.retention), "line_type": L.kind, "source_system": L.source_system})
contracts.to_csv(SIM / "billing_contracts.csv", index=False)
acc.drop(columns="customer_id").rename(columns={"name": "account_name", "vat": "vat_number"}).to_csv(SIM / "billing_accounts.csv", index=False)

# invoices: annual upfront or quarterly, services fees for new Enterprise / MSSP customers, a few credit notes
inv = []
n_inv = 0
for r in L.itertuples():
    step = 12 if r.billing_frequency == "annual" else 3
    p = pd.Period(r.start, "M")
    endp = pd.Period(r.end, "M")
    while p <= endp and p.to_timestamp() <= SIM_END:
        pe = min(p + step - 1, endp)
        months = (pe - p).n + 1
        n_inv += 1
        d = p.to_timestamp()
        late = rng.random() < 0.12
        paid = d + pd.Timedelta(days=int(rng.integers(25, 60) + (rng.integers(30, 90) if late else 0)))
        inv.append({"invoice_id": f"INV-{n_inv:06d}", "billing_account_id": r.billing_account_id, "contract_id": r.contract_id,
                    "invoice_date": d.date(), "service_period_start": d.date(), "service_period_end": pe.to_timestamp(how="end").date(),
                    "invoice_type": "subscription", "amount_excl_tax_eur": round(r.acv * months / 12, 2), "currency": "EUR",
                    "due_date": (d + pd.Timedelta(days=30)).date(), "paid_date": paid.date() if paid <= SIM_END else None})
        p = pe + 1
for r in L[(L.kind == "new")].itertuples():
    seg = cmap.loc[r.customer_id, "segment"]
    if seg in ("Enterprise", "MSSP", "Mid-market") and r.start >= pd.Timestamp("2024-12-01"):
        n_inv += 1
        d = r.start + pd.Timedelta(days=27)
        fee = {"Mid-market": 6000, "Enterprise": 18000, "MSSP": 24000}[seg]
        inv.append({"invoice_id": f"INV-{n_inv:06d}", "billing_account_id": r.billing_account_id, "contract_id": r.contract_id,
                    "invoice_date": d.date(), "service_period_start": d.date(), "service_period_end": d.date(),
                    "invoice_type": "professional_services", "amount_excl_tax_eur": float(fee), "currency": "EUR",
                    "due_date": (d + pd.Timedelta(days=30)).date(), "paid_date": (d + pd.Timedelta(days=40)).date() if d + pd.Timedelta(days=40) <= SIM_END else None})
I = pd.DataFrame(inv)
I = I[pd.to_datetime(I.invoice_date) <= SIM_END]
cn = I[(I.invoice_type == "subscription") & (pd.to_datetime(I.invoice_date) >= "2025-01-01")].sample(15, random_state=1)
credit = cn.assign(invoice_id=[f"CN-{j:05d}" for j in range(len(cn))], invoice_type="credit_note",
                   amount_excl_tax_eur=-(cn.amount_excl_tax_eur * 0.05).round(2),
                   invoice_date=(pd.to_datetime(cn.invoice_date) + pd.Timedelta(days=20)).dt.date,
                   service_period_start=(pd.to_datetime(cn.invoice_date) + pd.Timedelta(days=20)).dt.date,
                   service_period_end=(pd.to_datetime(cn.invoice_date) + pd.Timedelta(days=20)).dt.date)
I = pd.concat([I, credit], ignore_index=True)
I["vat_eur"] = (I.amount_excl_tax_eur * np.where(I.billing_account_id.map(acc.set_index("billing_account_id").country) == "FR", 0.2, 0.0)).round(2)
I.to_csv(SIM / "billing_invoices.csv", index=False)

# ------------------------------------------------------------------ CRM (HubSpot-like export)
crm_co = C[["crm_company_id", "name", "domain", "segment", "country"]].rename(columns={"name": "company_name"})
crm_co["lifecycle_stage"] = np.where(C.churn_date.notna() if "churn_date" in C else False, "former customer", "customer")
crm_co.to_csv(SIM / "crm_companies.csv", index=False)
deals = []
for r in L.itertuples():
    multi = r.term > 12 and r.kind != "upsell"
    tcv_entry = multi                                   # event 3: multi-year deals typed at total contract value
    amt = r.acv * (r.term / 12 if tcv_entry else 1)
    if rng.random() < 0.1:
        amt *= 1.05                                     # list price before the last discount, never updated
    close = r.start - pd.Timedelta(days=int(rng.integers(3, 40)))
    deals.append({"deal_id": f"D{r.line_id:06d}", "crm_company_id": cmap.loc[r.customer_id, "crm_company_id"],
                  "deal_name": f"{r.product} - {r.kind}", "deal_type": {"new": "New business", "renewal": "Renewal", "upsell": "Upsell"}[r.kind],
                  "pipeline_stage": "Closed won", "close_date": close.date(), "amount_eur": round(amt, -2),
                  "contract_term_months": r.term, "contract_start_date": r.start.date(), "owner_team": rng.choice(["Sales FR", "Sales EU", "Partners"])})
truth(3, "multi-year deals entered at total contract value in the CRM amount field", int(((L.term > 12) & (L.kind != "upsell")).sum()), "")
# closed-won deals with no contract in billing (handover gap) and open pipeline
for j in range(4):
    c = C.sample(1, random_state=100 + j).iloc[0]
    deals.append({"deal_id": f"D9{j:05d}", "crm_company_id": c.crm_company_id, "deal_name": "SOAR add-on - upsell", "deal_type": "Upsell",
                  "pipeline_stage": "Closed won", "close_date": pd.Timestamp("2026-10-20").date(), "amount_eur": 24000.0, "contract_term_months": 12,
                  "contract_start_date": pd.Timestamp("2026-11-01").date(), "owner_team": "Sales FR"})
for j in range(60):
    c = C.sample(1, random_state=200 + j).iloc[0]
    deals.append({"deal_id": f"D8{j:05d}", "crm_company_id": c.crm_company_id, "deal_name": "SOC platform - expansion", "deal_type": "Upsell",
                  "pipeline_stage": rng.choice(["Qualified", "Proposal", "Negotiation"]), "close_date": (pd.Timestamp("2026-12-01") + pd.Timedelta(days=int(rng.integers(0, 120)))).date(),
                  "amount_eur": float(round(rng.uniform(8000, 90000), -2)), "contract_term_months": 12, "contract_start_date": None, "owner_team": "Sales EU"})
pd.DataFrame(deals).to_csv(SIM / "crm_deals.csv", index=False)

# ------------------------------------------------------------------ product usage (platform export)
active_lines = L[L["product"] == "SOC platform"]
use = []
for m in MONTHS:
    me = M_END[m]
    act = active_lines[(active_lines.start <= me) & (active_lines.end >= me)].customer_id.unique()
    for cid in act:
        c = cmap.loc[cid]
        ret = int(c.retention)
        if cid in big_flat.customer_id.values and m >= RET_EXT:
            ret = 365
        ing = ingest_at(c, me) * rng.uniform(0.93, 1.07)
        ai = 0
        if c.ai_adopter and m >= AI_LAUNCH:
            ramp = min(1.0, ((m - AI_LAUNCH).n + 1) / 8)
            ai = int(ing * 40 * ramp * rng.uniform(0.6, 1.4))
        use.append({"month": str(m), "crm_company_id": c.crm_company_id, "tenant_id": f"T{int(cid[1:]):05d}",
                    "avg_ingest_gb_day": round(ing, 2), "retention_days": ret, "stored_gb": round(ing * min(ret, 30 + (m - pd.Period(c.first_start, 'M')).n * 31), 0),
                    "hosting_region": "OVH-FR" if c.public_sector else ("Azure-FR" if c.azure_region else "AWS-Paris"), "ai_queries": ai})
U = pd.DataFrame(use)
U.to_csv(SIM / "customer_usage.csv", index=False)

# ------------------------------------------------------------------ cloud bills in FOCUS v1.4 columns
fu = []


def focus_row(m, provider, service, cat, rid, rtype, sku, qty, unit, list_price, cur, disc, tags, invoice):
    lc = qty * list_price
    ec = lc * (1 - disc)
    fu.append({"BillingAccountId": {"AWS": "aws-billing-01", "Microsoft": "azure-ea-01", "OVHcloud": "ovh-nic-01"}[provider],
               "SubAccountId": {"AWS": "prod-eu-west-3", "Microsoft": "sub-prod-francecentral", "OVHcloud": "pci-prod-gra"}[provider],
               "BillingPeriodStart": str(M_START[m].date()), "ChargePeriodStart": str(M_START[m].date()),
               "ChargePeriodEnd": str((M_END[m] + pd.Timedelta(days=1)).date()), "ChargeCategory": "Usage",
               "ChargeDescription": f"{service} {sku}", "ServiceProviderName": provider, "ServiceName": service, "ServiceCategory": cat,
               "RegionId": {"AWS": "eu-west-3", "Microsoft": "francecentral", "OVHcloud": "GRA"}[provider], "ResourceId": rid, "ResourceType": rtype,
               "SkuId": sku, "ConsumedQuantity": round(qty, 3), "ConsumedUnit": unit, "PricingQuantity": round(qty, 3), "PricingUnit": unit,
               "ListUnitPrice": list_price, "ListCost": round(lc, 2), "EffectiveCost": round(ec, 2), "BilledCost": round(ec, 2),
               "BillingCurrency": cur, "PricingCurrency": cur, "InvoiceId": invoice, "Tags": json.dumps(tags) if tags else "{}"})


ug = U.groupby(["month", "hosting_region"]).agg(ingest=("avg_ingest_gb_day", "sum"), stored=("stored_gb", "sum"), ai=("ai_queries", "sum")).reset_index()
aws_eff = {m: 1.0 for m in MONTHS}                      # FinOps rightsizing factor on AWS compute, calibrated below (event 5)


def build_cloud():
    fu.clear()
    for m in MONTHS:
        g = ug[ug.month == str(m)].set_index("hosting_region")
        get = lambda reg, col: float(g.loc[reg, col]) if reg in g.index else 0.0
        h = HOURS[m]
        inv_aws, inv_az, inv_ovh = f"AWS-{m.strftime('%Y%m')}", f"AZ-{m.strftime('%Y%m')}", f"OVH-{m.strftime('%Y%m')}"
        disc = 0.10
        ing_aws, st_aws = get("AWS-Paris", "ingest") + get("Azure-FR", "ingest") * 0.6, get("AWS-Paris", "stored")
        nodes_ingest = ing_aws / 1000 * 3.5 * aws_eff[m]                     # r6i.2xlarge per TB/day ingested
        nodes_search = st_aws / 1e6 * 10.0 * aws_eff[m]                       # search nodes per PB kept searchable
        for j in range(4):
            focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "Compute", f"arn:aws:ec2:eu-west-3:ingest-{j}", "Instance", "r6i.2xlarge",
                      nodes_ingest / 4 * h, "Hours", PR["r6i"], "USD", disc, {"product": "siem", "component": "ingest", "env": "prod"}, inv_aws)
            focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "Compute", f"arn:aws:ec2:eu-west-3:search-{j}", "Instance", "r6i.2xlarge",
                      nodes_search / 4 * h, "Hours", PR["r6i"], "USD", disc, {"product": "siem", "component": "search", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "Compute", "arn:aws:ec2:eu-west-3:soar-workers", "Instance", "m6i.xlarge",
                  (6 + ing_aws / 1000 * 1.0) * h * aws_eff[m], "Hours", PR["m6i"], "USD", disc, {"product": "soar", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "Compute", "arn:aws:ec2:eu-west-3:cti-pipeline", "Instance", "c6i.2xlarge",
                  8 * h * aws_eff[m], "Hours", PR["c6i"], "USD", disc, {"product": "cti", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "Compute", "arn:aws:ec2:eu-west-3:staging", "Instance", "m6i.xlarge",
                  10 * h, "Hours", PR["m6i"], "USD", disc, {"env": "staging"}, inv_aws)
        focus_row(m, "AWS", "Amazon Simple Storage Service", "Storage", "arn:aws:s3:::logs-hot", "Bucket", "Standard",
                  st_aws * 0.35 * 3, "GB-Mo", PR["s3_std"], "USD", disc, {"product": "siem", "component": "storage", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon Simple Storage Service", "Storage", "arn:aws:s3:::logs-archive", "Bucket", "Standard - Infrequent Access",
                  st_aws * 0.65 * 3, "GB-Mo", PR["s3_ia"], "USD", disc, {"product": "siem", "component": "storage", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon CloudWatch", "Management and Governance", "arn:aws:logs:eu-west-3:platform", "Log group", "Logs ingested",
                  2000 + ing_aws * 0.4, "GB", 0.5, "USD", disc, {"product": "platform", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon Virtual Private Cloud", "Networking", "arn:aws:ec2:eu-west-3:nat-gateway", "NAT Gateway", "NAT data processed",
                  20000 + ing_aws * 3, "GB", 0.048, "USD", disc, {"product": "platform", "env": "prod"}, inv_aws)
        focus_row(m, "AWS", "Amazon Simple Storage Service", "Storage", "arn:aws:s3:::backups", "Bucket", "Standard - Infrequent Access",
                  150000 + st_aws * 0.05, "GB-Mo", PR["s3_ia"], "USD", disc, {"product": "platform", "component": "backup", "env": "prod"}, inv_aws)
        st_az = get("Azure-FR", "stored")
        focus_row(m, "Microsoft", "Azure Blob Storage", "Storage", "/subscriptions/prod/storage/logshot", "Storage Account", "Hot LRS",
                  st_az * 0.35 * 3, "1 GB/Month", PR["az_hot"], "EUR", 0.0, {"product": "siem", "component": "storage", "env": "prod"}, inv_az)
        focus_row(m, "Microsoft", "Azure Blob Storage", "Storage", "/subscriptions/prod/storage/logscool", "Storage Account", "Cool LRS",
                  st_az * 0.65 * 3, "1 GB/Month", PR["az_cool"], "EUR", 0.0, {"product": "siem", "component": "storage", "env": "prod"}, inv_az)
        ing_ovh, st_ovh = get("OVH-FR", "ingest"), get("OVH-FR", "stored")
        for j in range(2):
            focus_row(m, "OVHcloud", "Public Cloud Instances", "Compute", f"ovh-gra-siem-{j}", "Instance", "b3-16",
                      (4 + ing_ovh / 1000 * 9 + st_ovh / 1e6 * 24) / 2 * h, "Hours", PR["ovh_b316"], "EUR", 0.0, {"product": "siem", "env": "prod-sovereign"}, inv_ovh)
        focus_row(m, "OVHcloud", "Object Storage", "Storage", "ovh-gra-logs", "Bucket", "Standard",
                  st_ovh * 3, "GB-Mo", PR["ovh_obj"], "EUR", 0.0, {"product": "siem", "component": "storage", "env": "prod-sovereign"}, inv_ovh)
        focus_row(m, "OVHcloud", "Public Cloud Instances", "Compute", "ovh-gra-proxy", "Instance", "b3-16",
                  2 * h, "Hours", PR["ovh_b316"], "EUR", 0.0, {"product": "platform", "env": "prod-sovereign"}, inv_ovh)
        # event 7: AI feature costs, mostly untagged (resources created in a hurry at launch)
        ai_q = ug[ug.month == str(m)].ai.sum()
        if m >= AI_LAUNCH:
            focus_row(m, "OVHcloud", "AI Endpoints", "AI and Machine Learning", "ovh-ai-endpoints-llm", "Model endpoint", "Llama 3.3 70B tokens",
                      ai_q * 20000 / 1e6, "1M tokens", PR["ovh_tok"], "EUR", 0.0, None, inv_ovh)
            for j in range(3):
                focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "AI and Machine Learning", f"arn:aws:ec2:eu-west-3:gpu-{j}", "Instance", "g5.xlarge",
                          (1 + ai_q / 1.2e6) * h, "Hours", PR["g5"], "USD", disc, None, inv_aws)
            for j in range(2):
                focus_row(m, "AWS", "Amazon Elastic Compute Cloud", "Compute", f"arn:aws:ec2:eu-west-3:agents-{j}", "Instance", "m6i.xlarge",
                          (2 + ai_q / 3e6) * h, "Hours", PR["m6i"], "USD", disc, None if j == 0 else {"env": "prod"}, inv_aws)


def eur(df):
    return np.where(df.BillingCurrency == "USD", df.BilledCost / df.ChargePeriodStart.map(lambda s: FX[pd.Period(s[:7], "M")]), df.BilledCost)


def fx_share(f):
    for m in MONTHS:
        aws_eff[m] = f if str(m) >= "2026-09" else 1.0
    build_cloud()
    d = pd.DataFrame(fu)
    d["eur"] = eur(d)
    d["m"] = d.ChargePeriodStart.str[:7]
    a = d[d.ServiceProviderName == "AWS"]
    p0, p1 = a[a.m.isin(["2026-06", "2026-07", "2026-08"])], a[a.m.isin(["2026-09", "2026-10", "2026-11"])]
    rate0 = p0.BilledCost.sum() / p0.eur.sum()
    fx_eff = p1.eur.sum() - p1.BilledCost.sum() / rate0
    return fx_eff / (p1.eur.sum() - p0.eur.sum())


lo, hi = 0.7, 1.1                                     # bisection: FX explains 40% of the cloud cost rise (event 5)
for _ in range(40):
    mid = (lo + hi) / 2
    if fx_share(mid) > 0.40:
        lo = mid
    else:
        hi = mid
share = fx_share((lo + hi) / 2)
truth(5, "share of the AWS bill rise (EUR) Sep-Nov 2026 vs Jun-Aug 2026 explained by USD/EUR", round(share, 3), f"rightsizing factor {round((lo + hi) / 2, 3)}")
F = pd.DataFrame(fu)
F.to_csv(SIM / "cloud_costs_focus.csv", index=False)
last = F[F.ChargePeriodStart == "2026-11-01"]
truth(7, "share of cloud resources without any tag in Nov 2026", round((last.Tags == "{}").mean(), 3), "")
F["eur"] = eur(F)

# ------------------------------------------------------------------ HRIS (Lucca-like), payroll (SILAE-like), ATS (TeamTailor-like)
DEPTS = {"Engineering": (31, 40, 62000), "Product": (7, 10, 65000), "Threat Research": (11, 15, 60000), "SOC Operations & Support": (17, 27, 47000),
         "Customer Success": (9, 14, 50000), "Sales": (21, 29, 58000), "Marketing": (9, 12, 52000), "G&A": (15, 20, 55000)}
emp, n_emp = [], 0


def hire(dept, start, ctype="CDI"):
    global n_emp
    n_emp += 1
    lvl = rng.choice(["Junior", "Confirmed", "Senior", "Lead"], p=[0.25, 0.4, 0.25, 0.1])
    sal = DEPTS[dept][2] * {"Junior": 0.75, "Confirmed": 1.0, "Senior": 1.25, "Lead": 1.55}[lvl] * rng.uniform(0.92, 1.08)
    if ctype == "Intern":
        sal = 650 * 12
    if ctype == "Apprentice":
        sal = 1500 * 12
    emp.append({"employee_id": f"E{n_emp:04d}", "department": dept, "job_level": lvl if ctype in ("CDI", "CDD") else ctype,
                "contract_type": ctype, "start_date": start, "end_date": pd.NaT, "fte": 0.8 if (ctype == "CDI" and rng.random() < 0.06) else 1.0,
                "annual_gross_eur": round(sal, -2), "work_location": rng.choice(["Paris", "Rennes", "Remote FR"], p=[0.5, 0.35, 0.15])})
    return emp[-1]


for dept, (n0, _, _) in DEPTS.items():
    for _ in range(n0):
        hire(dept, pd.Timestamp("2022-06-01") + pd.Timedelta(days=int(rng.integers(0, 900))))
for _ in range(5):
    hire(rng.choice(list(DEPTS)), pd.Timestamp("2024-09-01"), "Apprentice")
for _ in range(4):
    hire(rng.choice(["Engineering", "Marketing", "G&A"]), pd.Timestamp("2024-09-01"), "Intern")
reqs, n_req = [], 0
for m in MONTHS:
    ms, me = M_START[m], M_END[m]
    frac = (m - MONTHS[0]).n / (len(MONTHS) - 1)
    for e in emp:                                         # leavers
        if pd.isna(e["end_date"]) and e["start_date"] < ms:
            if e["contract_type"] == "Intern" and (ms - e["start_date"]).days > 170:
                e["end_date"] = ms - pd.Timedelta(days=1)
            elif e["contract_type"] in ("CDI", "CDD") and rng.random() < 0.0095:
                e["end_date"] = me if rng.random() < 0.7 else ms + pd.Timedelta(days=14)
    for dept, (n0, n1, _) in DEPTS.items():               # hires to follow the plan
        target = round(n0 + (n1 - n0) * frac)
        act = sum(1 for e in emp if e["department"] == dept and e["contract_type"] in ("CDI", "CDD") and e["start_date"] <= me
                  and (pd.isna(e["end_date"]) or e["end_date"] > me))
        for _ in range(max(0, target - act)):
            ctype = "CDD" if rng.random() < 0.05 else "CDI"
            e = hire(dept, ms if rng.random() < 0.7 else ms + pd.Timedelta(days=14), ctype)
            n_req += 1
            opened = e["start_date"] - pd.Timedelta(days=int(rng.integers(45, 120)))
            reqs.append({"requisition_id": f"R{n_req:04d}", "department": dept, "job_level": e["job_level"], "opened_date": opened.date(),
                         "status": "Hired", "hired_date": (e["start_date"] - pd.Timedelta(days=30)).date(), "start_date": e["start_date"].date(),
                         "source": rng.choice(["Inbound", "Referral", "Agency", "Sourcing"], p=[0.45, 0.2, 0.15, 0.2]), "budgeted": True})
    if m.month == 9:
        for _ in range(6):
            hire(rng.choice(list(DEPTS)), ms, "Apprentice")
    if m.month in (3, 9):
        for _ in range(4):
            hire(rng.choice(["Engineering", "Marketing", "G&A", "Threat Research"]), ms, "Intern")
    if m.month == 9:
        for e in emp:
            if e["contract_type"] == "Apprentice" and pd.isna(e["end_date"]) and (ms - e["start_date"]).days > 700:
                e["end_date"] = ms - pd.Timedelta(days=1)
for j in range(14):                                       # open and cancelled requisitions
    n_req += 1
    reqs.append({"requisition_id": f"R{n_req:04d}", "department": rng.choice(list(DEPTS)), "job_level": "Confirmed",
                 "opened_date": (pd.Timestamp("2026-07-01") + pd.Timedelta(days=int(rng.integers(0, 130)))).date(),
                 "status": "Open" if j < 10 else "Cancelled", "hired_date": None, "start_date": None, "source": None, "budgeted": j < 12})
E = pd.DataFrame(emp)

# payroll register (one payslip per person and month)
pay = []
for m in MONTHS:
    ms, me = M_START[m], M_END[m]
    for e in emp:
        if e["start_date"] > me or (pd.notna(e["end_date"]) and e["end_date"] < ms):
            # final settlement paid the month after a month-end departure (60% of leavers)
            if pd.notna(e["end_date"]) and e["contract_type"] in ("CDI", "CDD") and pd.Period(e["end_date"], "M") == m - 1 \
                    and e["end_date"] == M_END[m - 1] and int(e["employee_id"][1:]) % 5 < 3:
                g = round(e["annual_gross_eur"] / 12 * 0.35, 2)
                pay.append({"pay_month": str(m), "employee_id": e["employee_id"], "payslip_type": "final_settlement", "gross_eur": g,
                            "employer_contrib_eur": round(g * 0.42, 2), "department": e["department"]})
            continue
        days_in = (min(me, e["end_date"] if pd.notna(e["end_date"]) else me) - max(ms, e["start_date"])).days + 1
        prorata = days_in / m.days_in_month
        g = e["annual_gross_eur"] / 12 * e["fte"] * prorata
        if e["department"] == "Sales" and e["contract_type"] == "CDI":
            g += e["annual_gross_eur"] / 12 * rng.uniform(0.1, 0.35)            # commissions
        if m.month == 3 and e["contract_type"] in ("CDI", "CDD"):
            g += e["annual_gross_eur"] * 0.06 * (e["start_date"] < ms - pd.Timedelta(days=180))   # annual bonus paid in March
        rate = {"CDI": 0.42, "CDD": 0.42, "Apprentice": 0.02, "Intern": 0.0}[e["contract_type"]]
        pay.append({"pay_month": str(m), "employee_id": e["employee_id"], "payslip_type": "regular", "gross_eur": round(g, 2),
                    "employer_contrib_eur": round(g * rate, 2), "department": e["department"]})
PY = pd.DataFrame(pay)
PY.drop(columns="department").to_csv(SIM / "payroll_monthly.csv", index=False)

# event 4 support + an extra data-quality issue: two leavers whose HRIS end date was never entered
stale = E[(E.end_date.notna()) & (E.contract_type == "CDI") & (E.end_date >= "2026-05-01") & (E.end_date < "2026-08-01")].head(2)
E_export = E.copy()
E_export.loc[stale.index, "end_date"] = pd.NaT
E_export["status"] = np.where(E_export.end_date.notna() & (E_export.end_date <= SIM_END), "Left", "Active")
E_export["start_date"], E_export["end_date"] = E_export.start_date.dt.date, E_export.end_date.dt.date
E_export.to_csv(SIM / "hris_employees.csv", index=False)
truth(4, "HRIS records still active after the person left (no payslip)", 2, ",".join(stale.employee_id))
pd.DataFrame(reqs).to_csv(SIM / "ats_requisitions.csv", index=False)

# ------------------------------------------------------------------ expenses (Navan-like)
exp, n_x = [], 0
travel_heavy = {"Sales": 9, "Customer Success": 5, "Marketing": 4, "SOC Operations & Support": 2}
for m in MONTHS:
    me = M_END[m]
    act = [e for e in emp if e["start_date"] <= me and (pd.isna(e["end_date"]) or e["end_date"] >= M_START[m]) and e["contract_type"] in ("CDI", "CDD")]
    for e in act:
        for _ in range(rng.poisson(travel_heavy.get(e["department"], 0.8))):
            n_x += 1
            d = M_START[m] + pd.Timedelta(days=int(rng.integers(0, m.days_in_month)))
            cat = rng.choice(["Travel", "Lodging", "Meals", "Software"], p=[0.4, 0.3, 0.25, 0.05])
            amt = {"Travel": 180, "Lodging": 140, "Meals": 45, "Software": 60}[cat] * rng.lognormal(0, 0.5)
            sub = d + pd.Timedelta(days=int(rng.integers(1, 12)))
            exp.append({"expense_id": f"X{n_x:06d}", "employee_id": e["employee_id"], "expense_date": d.date(), "submitted_date": sub.date(),
                        "approved_date": (sub + pd.Timedelta(days=int(rng.integers(1, 5)))).date(), "category": cat, "amount_eur": round(amt, 2),
                        "trip_tag": None})
# event 8: sales kick-off at the end of January 2026, expense reports submitted in February
sko_people = [e for e in emp if e["department"] in ("Sales", "Customer Success", "Marketing") and e["start_date"] <= pd.Timestamp("2026-01-26")
              and (pd.isna(e["end_date"]) or e["end_date"] >= pd.Timestamp("2026-01-31"))]
sko_total = 0
for e in sko_people:
    for cat, base in (("Travel", 420), ("Lodging", 520), ("Meals", 160)):
        n_x += 1
        amt = round(base * rng.uniform(0.8, 1.2), 2)
        sko_total += amt
        d = pd.Timestamp("2026-01-27")
        sub = pd.Timestamp("2026-02-02") + pd.Timedelta(days=int(rng.integers(0, 8)))
        exp.append({"expense_id": f"X{n_x:06d}", "employee_id": e["employee_id"], "expense_date": d.date(), "submitted_date": sub.date(),
                    "approved_date": (sub + pd.Timedelta(days=2)).date(), "category": cat, "amount_eur": amt, "trip_tag": "SKO-2026"})
X = pd.DataFrame(exp)
X.to_csv(SIM / "expenses.csv", index=False)
truth(8, "SKO travel incurred in Jan 2026, submitted and booked in Feb 2026 (EUR)", round(sko_total, 0), "")

# ------------------------------------------------------------------ general ledger (Pennylane-like, simplified French chart of accounts)
ACC = {"411000": "Clients", "487000": "Produits constates d'avance", "706000": "Abonnements SaaS", "706100": "Prestations de services",
       "709000": "Avoirs et rabais accordes", "512000": "Banque", "401000": "Fournisseurs", "421000": "Personnel - remunerations dues",
       "431000": "Securite sociale", "641000": "Remunerations du personnel", "641200": "Conges payes (provision)", "645000": "Charges de securite sociale",
       "428200": "Dettes provisionnees pour conges payes", "428600": "Personnel - autres charges a payer",
       "604100": "Hebergement cloud AWS", "604200": "Hebergement cloud Azure", "604300": "Hebergement cloud OVHcloud",
       "604500": "Flux de renseignement et outils de production", "625100": "Voyages et deplacements", "651000": "Licences logicielles internes",
       "623000": "Marketing et evenements", "613200": "Locations immobilieres", "622600": "Honoraires de recrutement", "628000": "Autres frais generaux",
       "101000": "Capital", "104000": "Primes d'emission"}
gl, n_e = [], 0


def post(date, journal, ref, lines_, label):
    global n_e
    n_e += 1
    assert abs(sum(d - c for _, d, c, _ in lines_)) < 0.02, (ref, lines_)
    for acct, dr, cr, analytic in lines_:
        gl.append({"entry_id": f"JE{n_e:06d}", "entry_date": pd.Timestamp(date).date(), "journal": journal, "account": acct,
                   "account_label": ACC[acct], "debit_eur": round(dr, 2), "credit_eur": round(cr, 2), "analytic_code": analytic,
                   "document_ref": ref, "label": label})


cash = []


def bank(date, amount, category, counterparty, ref):
    cash.append({"transaction_date": pd.Timestamp(date).date(), "bank_account": "Main EUR account", "amount_eur": round(amount, 2),
                 "category": category, "counterparty": counterparty, "reference": ref})


acc_country = acc.set_index("billing_account_id").country
for r in I.itertuples():
    d = pd.Timestamp(r.invoice_date)
    if d < M_START[MONTHS[0]]:
        continue
    a = r.amount_excl_tax_eur
    if r.invoice_type == "subscription":
        post(d, "VE", r.invoice_id, [("411000", a, 0, r.billing_account_id), ("487000", 0, a, r.contract_id)], "Subscription invoice")
    elif r.invoice_type == "professional_services":
        post(d, "VE", r.invoice_id, [("411000", a, 0, r.billing_account_id), ("706100", 0, a, r.contract_id)], "Onboarding services")
    else:
        post(d, "VE", r.invoice_id, [("709000", -a, 0, r.contract_id), ("411000", 0, -a, r.billing_account_id)], "Credit note")
    if pd.notna(r.paid_date) and pd.Timestamp(r.paid_date) <= SIM_END:
        bank(r.paid_date, a, "Customer receipts", r.billing_account_id, r.invoice_id)
        post(r.paid_date, "BQ", r.invoice_id, [("512000", a, 0, ""), ("411000", 0, a, r.billing_account_id)] if a > 0 else
             [("411000", -a, 0, r.billing_account_id), ("512000", 0, -a, "")], "Customer payment")
# revenue recognition: ratable by month over each invoice's service period (accounting keeps the true service dates)
sub = I[I.invoice_type == "subscription"]
late_cutoff = set(sub[(sub.invoice_date.astype(str) == "2026-06-01")].invoice_id.head(3))      # booked a month late
rec_rows = []
for r in sub.itertuples():
    p0, p1 = pd.Period(r.service_period_start, "M"), pd.Period(r.service_period_end, "M")
    n = (p1 - p0).n + 1
    for p in pd.period_range(p0, p1, freq="M"):
        if p in M_END:
            rec_rows.append((p, r.amount_excl_tax_eur / n, r.contract_id, r.invoice_id))
REC = pd.DataFrame(rec_rows, columns=["month", "amount", "contract_id", "invoice_id"])
for m in MONTHS:
    x = REC[REC.month == m]
    book = x[~((x.invoice_id.isin(late_cutoff)) & (m == pd.Period("2026-06", "M")))].amount.sum()
    if m == pd.Period("2026-07", "M"):
        book += REC[(REC.invoice_id.isin(late_cutoff)) & (REC.month == pd.Period("2026-06", "M"))].amount.sum()
    post(M_END[m], "OD", f"REVREC-{m}", [("487000", book, 0, ""), ("706000", 0, book, "")], "Monthly subscription revenue recognition")
truth(9, "extra: 3 June 2026 subscription invoices recognised in July (cut-off)", 3, ",".join(sorted(late_cutoff)))

# payroll journal, by department
dep_of = E.set_index("employee_id").department
for m in MONTHS:
    x = PY[PY.pay_month == str(m)]
    for dept, g in x.groupby("department"):
        gross, contrib = g.gross_eur.sum(), g.employer_contrib_eur.sum()
        post(M_END[m], "PA", f"PAY-{m}-{dept[:3].upper()}", [("641000", gross, 0, dept), ("645000", contrib, 0, dept),
             ("421000", 0, gross * 0.78, dept), ("431000", 0, gross * 0.22 + contrib, dept)], "Payroll journal")
    tot = x.gross_eur.sum()
    bank(M_END[m] - pd.Timedelta(days=2), -tot * 0.78, "Payroll - net salaries", "Employees", f"PAY-{m}")
    post(M_END[m] - pd.Timedelta(days=2), "BQ", f"PAY-{m}", [("421000", tot * 0.78, 0, ""), ("512000", 0, tot * 0.78, "")], "Net salaries paid")
    soc = tot * 0.22 + x.employer_contrib_eur.sum()
    pdate = M_END[m] + pd.Timedelta(days=15)
    if pdate <= SIM_END:
        bank(pdate, -soc, "Payroll - social charges", "URSSAF and pension funds", f"SOC-{m}")
        post(pdate, "BQ", f"SOC-{m}", [("431000", soc, 0, ""), ("512000", 0, soc, "")], "Social charges paid")
    cp = tot * (0.012 if m.month not in (7, 8) else -0.03)                          # paid-leave accrual movement
    post(M_END[m], "OD", f"CP-{m}", [("641200", cp, 0, ""), ("428200", 0, cp, "")] if cp > 0 else [("428200", -cp, 0, ""), ("641200", 0, -cp, "")], "Paid-leave accrual")
bonus_acc = round(PY[(PY.pay_month == "2026-03") & (PY.payslip_type == "regular")].gross_eur.sum() - PY[(PY.pay_month == "2026-02")].gross_eur.sum(), -3)
post("2025-12-31", "OD", "BONUS-ACCRUAL-2025", [("641000", bonus_acc, 0, "All"), ("428600", 0, bonus_acc, "")], "Year-end bonus accrual")
post("2026-03-31", "OD", "BONUS-ACCRUAL-2025-REV", [("428600", bonus_acc, 0, ""), ("641000", 0, bonus_acc, "All")], "Reversal of bonus accrual")

# cloud bills: AWS converted at the ECB monthly rate; the Azure bill of May 2026 is booked in June (cut-off)
for (inv_id, provider), g in F.groupby(["InvoiceId", "ServiceProviderName"]):
    m = pd.Period(g.ChargePeriodStart.iloc[0][:7], "M")
    eur_amt = g.eur.sum()
    acct = {"AWS": "604100", "Microsoft": "604200", "OVHcloud": "604300"}[provider]
    d = M_END[m] if not (provider == "Microsoft" and m == pd.Period("2026-05", "M")) else pd.Timestamp("2026-06-05")
    post(d, "AC", inv_id, [(acct, eur_amt, 0, provider), ("401000", 0, eur_amt, provider)], f"{provider} invoice")
    pdate = M_END[m] + pd.Timedelta(days=20)
    if pdate <= SIM_END:
        bank(pdate, -eur_amt, "Cloud providers", provider, inv_id)
        post(pdate, "BQ", inv_id, [("401000", eur_amt, 0, provider), ("512000", 0, eur_amt, "")], f"{provider} payment")
truth(10, "extra: Azure bill of May 2026 booked in June (cut-off)", 1, "AZ-202605")

# expenses booked on approval date, reimbursed the following 10th
X["approved_date"] = pd.to_datetime(X.approved_date)
for m in MONTHS:
    x = X[(X.approved_date >= M_START[m]) & (X.approved_date <= M_END[m])]
    if len(x):
        post(M_END[m], "OD", f"EXP-{m}", [("625100", x.amount_eur.sum(), 0, "Expenses"), ("421000", 0, x.amount_eur.sum(), "")], "Expense reports approved")
        pdate = M_END[m] + pd.Timedelta(days=10)
        if pdate <= SIM_END:
            bank(pdate, -x.amount_eur.sum(), "Expense reimbursements", "Employees", f"EXP-{m}")
            post(pdate, "BQ", f"EXP-{m}", [("421000", x.amount_eur.sum(), 0, ""), ("512000", 0, x.amount_eur.sum(), "")], "Expense reimbursements")

# other operating costs (suppliers)
hires_by_m = E[(E.contract_type.isin(["CDI", "CDD"])) & (E.start_date >= M_START[MONTHS[0]])].groupby(E.start_date.dt.to_period("M")).size()
for m in MONTHS:
    t = (m - MONTHS[0]).n
    items = {"604500": 22000 + 300 * t, "651000": 80000 + 700 * t, "623000": 320000 * (1.6 if m.month in (3, 10) else 1.0) * rng.uniform(0.85, 1.15),
             "613200": 62000 if m < pd.Period("2025-09", "M") else 78000, "622600": 9000 * int(hires_by_m.get(m, 0)) * 0.3,
             "628000": 150000 * rng.uniform(0.85, 1.15)}
    for acct, amt in items.items():
        if amt <= 0:
            continue
        post(M_END[m], "AC", f"SUP-{acct}-{m}", [(acct, amt, 0, "Suppliers"), ("401000", 0, amt, "")], ACC[acct])
        pdate = M_END[m] + pd.Timedelta(days=25)
        if pdate <= SIM_END:
            bank(pdate, -amt, "Suppliers", ACC[acct], f"SUP-{acct}-{m}")
            post(pdate, "BQ", f"SUP-{acct}-{m}", [("401000", amt, 0, ""), ("512000", 0, amt, "")], "Supplier payment")
# simulated funding round and opening balance
bank("2024-12-01", 8_500_000, "Opening balance", "Bank", "OPENING")
post("2024-12-01", "OD", "OPENING", [("512000", 8_500_000, 0, ""), ("101000", 0, 8_500_000, "")], "Opening bank balance (simplified)")
bank("2025-04-15", 20_000_000, "Financing", "Investors (simulated round)", "EQUITY-2025")
post("2025-04-15", "BQ", "EQUITY-2025", [("512000", 20_000_000, 0, ""), ("101000", 0, 2_500_000, ""), ("104000", 0, 17_500_000, "")], "Equity round (simulated)")
# one bank fee line never booked in the ledger
bank("2026-10-31", -1840.0, "Bank fees", "Bank", "FEES-2026-10")
truth(11, "extra: bank fee in Oct 2026 missing from the ledger (EUR)", 1840, "FEES-2026-10")
GL = pd.DataFrame(gl)
GL.to_csv(SIM / "gl_entries.csv", index=False)
CASH = pd.DataFrame(cash).sort_values("transaction_date")
CASH.to_csv(SIM / "cash_transactions.csv", index=False)

# ------------------------------------------------------------------ budget 2026 (Pigment-like export), built in Dec 2025
bud = []
glm = GL.assign(month=pd.to_datetime(GL.entry_date).dt.to_period("M"))
act25 = lambda acct: glm[(glm.account == acct) & (glm.month == pd.Period("2025-11", "M"))].eval("debit_eur - credit_eur").sum()
aws_nov = F[(F.ServiceProviderName == "AWS") & (F.ChargePeriodStart == "2025-11-01")]
rev_nov = -act25("706000")
for m in pd.period_range("2026-01", "2026-12", freq="M"):
    t = (m - pd.Period("2025-11", "M")).n
    rows = {
        ("Revenue", "SaaS subscriptions", "706000"): rev_nov * 1.021 ** t,
        ("Revenue", "Professional services", "706100"): 60000,
        ("COGS", "Cloud hosting - Azure", "604200"): act25("604200") * 1.02 ** t,
        ("COGS", "Cloud hosting - OVHcloud", "604300"): act25("604300") * 1.025 ** t,
        ("COGS", "Threat-intel feeds and production tools", "604500"): 26000 + 300 * t,
        ("Opex", "Travel and expenses", "625100"): (act25("625100") + (sko_total if m == SKO else 0)) * 1.0,
        ("Opex", "Internal software", "651000"): 85000 + 700 * t,
        ("Opex", "Marketing and events", "623000"): 330000 * (1.6 if m.month in (3, 10) else 1.0),
        ("Opex", "Rent", "613200"): 78000,
        ("Opex", "Recruiting fees", "622600"): 12000,
        ("Opex", "Other G&A", "628000"): 150000,
    }
    for (grp, line, acct), v in rows.items():
        bud.append({"month": str(m), "line_group": grp, "budget_line": line, "gl_account": acct, "budget_eur": round(v, 0),
                    "aws_list_cost_usd": None, "aws_discount_rate": None, "usd_per_eur": None, "headcount": None, "department": None})
    lc = aws_nov.ListCost.sum() * 1.025 ** t                 # AWS: volume at list price, discount and FX rate are explicit
    bud.append({"month": str(m), "line_group": "COGS", "budget_line": "Cloud hosting - AWS", "gl_account": "604100",
                "budget_eur": round(lc * (1 - 0.15) / 1.17, 0), "aws_list_cost_usd": round(lc, 0), "aws_discount_rate": 0.15, "usd_per_eur": 1.17,
                "headcount": None, "department": None})
    for dept, (n0, n1, sal) in DEPTS.items():
        hc = round(n0 + (n1 - n0) * ((m - MONTHS[0]).n / (len(MONTHS) - 1)) + (1 if dept in ("Engineering", "Sales") else 0))
        bud.append({"month": str(m), "line_group": "Payroll", "budget_line": f"Payroll - {dept}", "gl_account": "641000+645000",
                    "budget_eur": round(hc * sal * 1.05 / 12 * 1.42 * (1.25 if dept == "Sales" else 1.0) + (hc * sal * 0.06 * 1.42 if m.month == 3 else 0), 0),
                    "aws_list_cost_usd": None, "aws_discount_rate": None, "usd_per_eur": None, "headcount": hc, "department": dept})
pd.DataFrame(bud).to_csv(SIM / "budget_2026.csv", index=False)

pd.DataFrame(TRUTH).to_csv(ROOT / "data" / "_hidden_truth.csv", index=False)
act = lambda d: L[(L.start <= d) & (L.end >= d)]
print("customers active Nov-26:", act(SIM_END).customer_id.nunique(), "| ARR Nov-26 (truth): EUR", round(act(SIM_END).acv.sum() / 1e6, 2), "M",
      "| ARR Dec-24:", round(act(pd.Timestamp('2024-12-31')).acv.sum() / 1e6, 2), "M")
hc = E[(E.contract_type != "Intern") & (E.start_date <= SIM_END) & (E.end_date.isna() | (E.end_date > SIM_END))]
print("headcount Nov-26:", len(hc), "| cloud EUR Nov-26:", round(F[F.ChargePeriodStart == '2026-11-01'].eur.sum()), "| AI EUR:",
      round(F[(F.ChargePeriodStart == '2026-11-01') & (F.ServiceCategory == 'AI and Machine Learning')].eur.sum()),
      "| payroll Nov-26:", round(PY[PY.pay_month == '2026-11'][["gross_eur", "employer_contrib_eur"]].sum().sum()))
print("untagged Nov:", TRUTH[-1]["value"] if False else round((last.Tags == "{}").mean(), 3), "| AI share cloud:", round(F[(F.ChargePeriodStart == "2026-11-01") & (F.ServiceCategory == "AI and Machine Learning")].eur.sum() / F[F.ChargePeriodStart == "2026-11-01"].eur.sum(), 3))
print("cash end:", round(CASH.amount_eur.sum() / 1e6, 2), "M | truth rows:", len(TRUTH), "| FX share:", round(share, 3))
for f in sorted(SIM.glob("*.csv")):
    print(f.name, len(pd.read_csv(f, usecols=[0])))
