"""Collect the public data used by the case study (no key, no account, neutral User-Agent).

Raw responses are kept in data/raw/ (not published) so each source is called once; tidy extracts go to data/public/.
    python src/fetch_public.py
Sources: SEC EDGAR XBRL company facts, AWS Price List (Paris region), Azure Retail Prices (France Central),
OVHcloud public catalog, FOCUS v1.4 specification (GitHub), ECB exchange rates, Nager.Date holidays,
French company register API (recherche-entreprises.api.gouv.fr, identity fields only).
"""
import csv
import io
import json
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW, PUB = ROOT / "data" / "raw", ROOT / "data" / "public"
RAW.mkdir(parents=True, exist_ok=True)
PUB.mkdir(parents=True, exist_ok=True)
S = requests.Session()
S.headers["User-Agent"] = "finance-data-case-study/1.0"

SEC = {"CrowdStrike": "0001535527", "SentinelOne": "0001583708", "Rapid7": "0001560327", "Tenable": "0001660280"}
EC2_TYPES = ["m6i.xlarge", "r6i.2xlarge", "c6i.2xlarge", "g5.xlarge"]
FOCUS_USED = ["BilledCost", "EffectiveCost", "ListCost", "ListUnitPrice", "BillingCurrency", "BillingAccountId",
              "BillingPeriodStart", "ChargePeriodStart", "ChargePeriodEnd", "ChargeCategory", "ChargeDescription",
              "ServiceProviderName", "ServiceName", "ServiceCategory", "RegionId", "ResourceId", "ResourceType",
              "SkuId", "ConsumedQuantity", "ConsumedUnit", "PricingQuantity", "PricingUnit", "PricingCurrency",
              "SubAccountId", "InvoiceId", "Tags"]


def get(url, name, **kw):
    """Download once; later runs read data/raw/<name>."""
    f = RAW / name
    if not f.exists():
        r = S.get(url, timeout=120, **kw)
        r.raise_for_status()
        f.write_bytes(r.content)
        time.sleep(0.2)          # SEC asks for <= 10 requests/second; we stay far below
    return f


# ------------------------------------------------------------------ SEC EDGAR (10-K only)
def sec():
    tags = {"revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenues"],
            "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold"],
            "rnd": ["ResearchAndDevelopmentExpense"],
            "sales_marketing": ["SellingAndMarketingExpense"],
            "deferred_revenue_current": ["ContractWithCustomerLiabilityCurrent"],
            "deferred_revenue_noncurrent": ["ContractWithCustomerLiabilityNoncurrent"]}
    rows = []
    for co, cik in SEC.items():
        d = json.loads(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", f"sec_CIK{cik}.json").read_text(encoding="utf-8"))
        g = d["facts"].get("us-gaap", {})
        for metric, cands in tags.items():
            found = []
            for rank, t in enumerate(cands):    # a company can change tag over time: merge candidates, first one wins per period
                for x in g.get(t, {}).get("units", {}).get("USD", []):
                    if x.get("form") != "10-K" or x.get("fp") != "FY":
                        continue
                    if "start" in x and not 350 <= (pd.Timestamp(x["end"]) - pd.Timestamp(x["start"])).days <= 380:
                        continue                 # flow: keep full-year periods only
                    found.append({**x, "tag": t, "rank": rank})
            if found:
                df = pd.DataFrame(found).sort_values(["end", "rank", "filed"], ascending=[True, True, False]).drop_duplicates("end")
                for x in df.itertuples():
                    rows.append({"company": co, "cik": cik, "entity_name": d["entityName"], "metric": metric, "xbrl_tag": x.tag,
                                 "period_end": x.end, "value_usd": x.val, "form": x.form, "filed": x.filed, "accession": x.accn})
    out = pd.DataFrame(rows)
    out = out[out.period_end >= "2022-01-01"]
    out.to_csv(PUB / "sec_benchmarks_long.csv", index=False)
    w = out.pivot_table(index=["company", "period_end"], columns="metric", values="value_usd").reset_index()
    w = w.dropna(subset=["revenue", "cost_of_revenue"])
    w["gross_margin"] = 1 - w.cost_of_revenue / w.revenue
    w["rnd_pct_revenue"] = w.rnd / w.revenue
    w["sm_pct_revenue"] = w.sales_marketing / w.revenue
    w["deferred_rev_pct_revenue"] = (w.deferred_revenue_current + w.deferred_revenue_noncurrent.fillna(0)) / w.revenue
    w.to_csv(PUB / "sec_benchmarks.csv", index=False)
    print("SEC", w.groupby("company").period_end.max().to_dict())


# ------------------------------------------------------------------ cloud prices
def aws():
    d = json.loads(get("https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/eu-west-3/index.json",
                       "aws_s3_eu-west-3.json").read_text(encoding="utf-8"))
    rows = []
    for sku, p in d["products"].items():
        a = p["attributes"]
        if a.get("volumeType") in ("Standard", "Standard - Infrequent Access"):
            for t in d["terms"]["OnDemand"].get(sku, {}).values():
                for dim in t["priceDimensions"].values():
                    rows.append({"provider": "AWS", "region": "eu-west-3 (Paris)", "service": "Amazon S3", "sku": a["volumeType"],
                                 "unit": dim["unit"], "begin_range": dim["beginRange"], "end_range": dim["endRange"],
                                 "price": float(dim["pricePerUnit"]["USD"]), "currency": "USD", "published": d["publicationDate"]})
    # EC2: ~170 MB CSV, streamed and filtered line by line, only the kept rows are written to disk
    f = RAW / "aws_ec2_eu-west-3_filtered.csv"
    if not f.exists():
        r = S.get("https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/eu-west-3/index.csv", stream=True, timeout=600)
        r.raise_for_status()
        lines = (b.decode("utf-8") for b in r.iter_lines())
        meta = [next(lines) for _ in range(5)]
        header = next(csv.reader([next(lines)]))
        ix = {h: i for i, h in enumerate(header)}
        kept = []
        for line in lines:
            if not any(t in line for t in EC2_TYPES):
                continue
            v = next(csv.reader([line]))
            if (v[ix["TermType"]] == "OnDemand" and v[ix["Instance Type"]] in EC2_TYPES and v[ix["Operating System"]] == "Linux"
                    and v[ix["Tenancy"]] == "Shared" and v[ix["Pre Installed S/W"]] == "NA" and v[ix["CapacityStatus"]] == "Used"):
                kept.append({"instance_type": v[ix["Instance Type"]], "vcpu": v[ix["vCPU"]], "memory": v[ix["Memory"]],
                             "unit": v[ix["Unit"]], "price": v[ix["PricePerUnit"]], "currency": v[ix["Currency"]]})
        pd.DataFrame(kept).assign(published=[m for m in meta if "Publication" in m][0].split(",")[-1].strip('"')).to_csv(f, index=False)
    ec2 = pd.read_csv(f)
    for x in ec2.itertuples():
        rows.append({"provider": "AWS", "region": "eu-west-3 (Paris)", "service": "Amazon EC2", "sku": f"{x.instance_type} ({x.vcpu} vCPU, {x.memory})",
                     "unit": x.unit, "begin_range": 0, "end_range": "Inf", "price": x.price, "currency": x.currency, "published": x.published})
    return rows


def azure():
    f = RAW / "azure_storage_francecentral.json"
    if not f.exists():
        url = ("https://prices.azure.com/api/retail/prices?currencyCode='EUR'&$filter=serviceName eq 'Storage' and "
               "armRegionName eq 'francecentral' and productName eq 'General Block Blob v2'")
        items = []
        while url and len(items) < 5000:
            r = S.get(url, timeout=60)
            r.raise_for_status()
            j = r.json()
            items += j["Items"]
            url = j.get("NextPageLink")
            time.sleep(0.3)
        f.write_text(json.dumps(items), encoding="utf-8")
    items = json.loads(f.read_text(encoding="utf-8"))
    rows = []
    for x in items:
        if x["meterName"] in ("Hot LRS Data Stored", "Cool LRS Data Stored", "Archive LRS Data Stored") and x["type"] == "Consumption" \
                and x.get("tierMinimumUnits", 0) == 0:
            rows.append({"provider": "Azure", "region": "francecentral", "service": "Blob Storage (General Block Blob v2)",
                         "sku": x["meterName"], "unit": x["unitOfMeasure"], "begin_range": 0, "end_range": "Inf",
                         "price": x["retailPrice"], "currency": x["currencyCode"], "published": x["effectiveStartDate"][:10]})
    return rows


def ovh():
    d = json.loads(get("https://eu.api.ovh.com/v1/order/catalog/public/cloud?ovhSubsidiary=FR", "ovh_catalog_cloud_FR.json").read_text(encoding="utf-8"))
    want = {"storage-standard.monthly.postpaid": ("Object Storage Standard (S3 API)", "GB-month"),
            "archive.monthly.postpaid": ("Cold Archive", "GB-month"),
            "b3-8.consumption": ("Instance b3-8 (2 vCPU, 8 GB)", "hour"),
            "b3-16.consumption": ("Instance b3-16 (4 vCPU, 16 GB)", "hour"),
            "r3-32.consumption": ("Instance r3-32 (2 vCPU, 32 GB)", "hour"),
            "c3-8.consumption": ("Instance c3-8 (4 vCPU, 8 GB)", "hour")}
    rows = []
    for a in d["addons"]:
        pc = a["planCode"]
        if pc in want and a["pricings"]:
            rows.append({"provider": "OVHcloud", "region": "FR catalog", "service": "Public Cloud", "sku": want[pc][0], "unit": want[pc][1],
                         "begin_range": 0, "end_range": "Inf", "price": a["pricings"][0]["price"] / 1e8, "currency": "EUR (excl. VAT)",
                         "published": "catalog read " + time.strftime("%Y-%m-%d")})
        if pc.startswith("ai-endpoints.") and "llama-3-3-70b" in pc and ("input_tokens" in pc or "output_tokens" in pc) and a["pricings"]:
            rows.append({"provider": "OVHcloud", "region": "FR catalog", "service": "AI Endpoints (Llama 3.3 70B)",
                         "sku": "input tokens" if "input" in pc else "output tokens", "unit": "1M tokens", "begin_range": 0, "end_range": "Inf",
                         "price": a["pricings"][0]["price"] / 1e8 * 1e6, "currency": "EUR (excl. VAT)", "published": "catalog read " + time.strftime("%Y-%m-%d")})
    return rows


def prices():
    p = pd.DataFrame(aws() + azure() + ovh())
    p.to_csv(PUB / "cloud_unit_prices.csv", index=False)
    print("prices", p.groupby("provider").size().to_dict())


# ------------------------------------------------------------------ FOCUS, FX, holidays, register
def focus():
    f = get("https://api.github.com/repos/FinOps-Open-Cost-and-Usage-Spec/FOCUS_Spec/contents/specification/datasets/cost_and_usage/columns?ref=v1.4",
            "focus_v1_4_columns.json")
    spec = {x["name"].removesuffix(".md") for x in json.loads(f.read_text(encoding="utf-8"))}
    df = pd.DataFrame({"column": FOCUS_USED, "in_focus_v1_4": [c.lower() in spec for c in FOCUS_USED]})
    df.to_csv(PUB / "focus_columns_used.csv", index=False)
    assert df.in_focus_v1_4.all(), df[~df.in_focus_v1_4]
    print("FOCUS columns verified", len(df))


def fx():
    f = get("https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A?startPeriod=2024-01&format=csvdata", "ecb_usd_eur.csv")
    d = pd.read_csv(f)[["TIME_PERIOD", "OBS_VALUE"]].rename(columns={"TIME_PERIOD": "month", "OBS_VALUE": "usd_per_eur"})
    d.to_csv(PUB / "ecb_usd_eur_monthly.csv", index=False)
    print("FX months", len(d), d.month.min(), d.month.max())


def holidays():
    out = []
    for y in (2024, 2025, 2026, 2027):
        out += json.loads(get(f"https://date.nager.at/api/v3/PublicHolidays/{y}/FR", f"holidays_FR_{y}.json").read_text(encoding="utf-8"))
    d = pd.DataFrame(out)
    d = d[d.global_.fillna(True) if "global_" in d else d["global"]][["date", "localName", "name"]]
    d.to_csv(PUB / "fr_public_holidays.csv", index=False)


def register():
    """Identity fields only. The response also lists company officers: they are never written to disk."""
    r = S.get("https://recherche-entreprises.api.gouv.fr/search", params={"q": "sekoia.io"}, timeout=60)
    r.raise_for_status()
    x = next(c for c in r.json()["results"] if c["siren"] == "913174744")
    keep = {"name": x["nom_complet"], "siren": x["siren"], "created": x.get("date_creation"),
            "head_office_city": x["siege"].get("libelle_commune"), "naf_code": x.get("activite_principale"),
            "company_category": x.get("categorie_entreprise"), "headcount_band_code": x.get("tranche_effectif_salarie"),
            "headcount_band_year": x.get("annee_tranche_effectif_salarie"), "read_on": time.strftime("%Y-%m-%d"),
            "source": "https://recherche-entreprises.api.gouv.fr (French company register, SIRENE)"}
    (PUB / "company_register.json").write_text(json.dumps(keep, indent=1), encoding="utf-8")
    print("register", keep["name"], keep["created"], keep["head_office_city"], keep["headcount_band_code"])


if __name__ == "__main__":
    sec()
    prices()
    focus()
    fx()
    holidays()
    register()
