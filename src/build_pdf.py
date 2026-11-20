"""Build the 8-page PDF report: charts (src/charts.py) -> HTML pages (16:9) -> PDF with headless Edge or Chrome.

Every number on the pages is read from data/marts/headline.json, the marts or data/public, so the report always matches the code.
    python src/build_pdf.py
Outputs: report/report.html, report/Sekoia_Finance_Data_CaseStudy.pdf (empty author metadata)
"""
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter

import charts

ROOT = Path(__file__).resolve().parents[1]
REP, MARTS, PUB = ROOT / "report", ROOT / "data" / "marts", ROOT / "data" / "public"
PDF_NAME = "Sekoia_Finance_Data_CaseStudy.pdf"
COLLECTED = "public data read 19-20 Nov 2026"
DISCLAIMER = "Independent case study based on public data · not affiliated with or endorsed by Sekoia"
AI_NOTE = next(l[2:].strip() for l in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if l.startswith("- AI-assisted workflow:"))


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def meur(x, d=1):
    return f"€{x / 1e6:,.{d}f}M"


def keur(x):
    return f"€{x / 1e3:,.0f}k"


def page(n, title, subtitle, tags, body, sources):
    t = "".join(f'<div class="tag tag-{x.lower().split()[0]}">{x}</div>' for x in tags)
    return f"""
<section class="page">
  <header><div><h1>{title}</h1><p class="sub">{subtitle}</p></div><div class="tags">{t}</div></header>
  <main>{body}</main>
  <footer><span>{sources} · {COLLECTED}</span><span>{DISCLAIMER}</span><span>{n}</span></footer>
</section>"""


def card(inner, cls=""):
    return f'<div class="card {cls}">{inner}</div>'


def img(src, cap=""):
    return f'<figure><img src="{src}"/>{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'


def tile(label, value, text):
    return card(f'<div class="label">{label}</div><div class="big">{value}</div><p>{text}</p>', "tile")


def p0(h, ch):
    tiles = "".join([
        tile("SIMULATED · PAGE 3", f"{meur(h['crm_arr_nov26'])} vs {meur(h['arr_nov26'])}",
             f"CRM vs billing ARR, Nov 2026. Fully explained: {h['multi_year_deals_tcv']} multi-year deals typed at total contract value, "
             f"old discounts, {h['orphan_deals_nov26']} deals without contract."),
        tile("SIMULATED · PAGE 3", f"NRR {pct(h['nrr_raw_mar26'])} → {pct(h['nrr_clean_mar26'])}",
             f"March 2026 'churn' on the raw billing export: {h['migration_gap_lines']} renewals closed one day early by a tool migration. Not escalated."),
        tile("SIMULATED · PAGE 4", f"{pct(h['nrr_clean_nov26'], 1)} / {pct(h['grr_clean_nov26'], 1)}",
             f"NRR / GRR, trailing 12 months, Nov 2026. ARR {meur(h['arr_nov26'])}, +{pct(h['arr_growth_yoy'])} a year, {h['customers_nov26']} customers."),
        tile("SIMULATED + PUBLIC · PAGE 5", f"{h['underwater_customers_nov26']} customers < 0",
             f"flat fee, logs kept 365 days instead of 120, no repricing: storage x{h['retention_storage_x']:.1f}, margin "
             f"{pct(h['retention_customers_gm_jun25'])} → {pct(h['retention_customers_gm_nov26'])}."),
    ])
    q = card(f"""<h2>Five questions</h2><ol class="qs">
      <li><b>Map</b> Which systems hold Finance data, who owns them, how do they join? <span class="pg">p.2</span></li>
      <li><b>Definitions</b> Why does ARR have three values, and which one is the reference? <span class="pg">p.3</span></li>
      <li><b>Growth</b> Does growth hold once the data is reconciled (ARR bridge, NRR, GRR)? <span class="pg">p.4</span></li>
      <li><b>Cost</b> What does a customer really cost: storage, retention, AI, untagged cloud? <span class="pg">p.5</span></li>
      <li><b>Close</b> Can the month be closed with confidence: budget, FX, headcount, cash? <span class="pg">p.6</span></li></ol>
      <p class="reco"><b>Recommendations:</b> (1) take ARR from billing contracts on one customer key (VAT number), never from CRM amounts;
      (2) add an annual value field in the CRM and keep TCV apart; (3) run the 6 reconciliations at D+2 with thresholds and publish only
      when tests pass; (4) reprice retention above contract at renewal and track cost to serve per customer monthly;
      (5) enforce cloud tags at deploy and split every cloud variance into price, volume and FX.</p>""", "wide roomy")
    meth = card(f"""<h2>Data &amp; method</h2>
      <p><b class="k">PUBLIC</b> Sekoia's own statements (website, job post), SEC 10-K figures of 4 listed security vendors, AWS / Azure /
      OVHcloud list prices, FOCUS v1.4 column names, ECB USD/EUR rates, French public holidays.</p>
      <p><b class="k">SIMULATED</b> a fictional 180-person cybersecurity SaaS (~400 customers, 24 months): 12 exports inspired by the tools
      named in the job post, with 8 planted data problems. Realistic patterns, <u>not</u> Sekoia's numbers.</p>
      <p><b class="k">METHOD</b> SQL warehouse in layers (DuckDB), 23 automated tests, reconciliations as cascades, unit economics by
      cost driver, price / volume / FX split, Excel pack that audits itself, HTML dashboard, Metabase queries.</p>""", "wide roomy")
    how = card("""<h3>How to read this report</h3><p><b>Titles</b> state the conclusion. <b>Tags</b> PUBLIC DATA / SIMULATED mark where data
      come from. <b>Blue</b> = the reference number; <b>orange / grey</b> = the same metric from another source; <b>red</b> = alert or threshold.</p>""", "how auto")
    body = f'<div class="grid4">{tiles}</div><div class="g0">{q}<div class="stack">{meth}{how}</div></div>'
    return page(0, "ARR, headcount and costs can be trusted once they come from one definition and reconcile every month",
                "Overview: four findings on a simulated scale-up that runs on the same tools as Sekoia's Finance team.",
                ["OVERVIEW"], body, "README.md, docs/")


def p1(h, ch):
    f = pd.read_csv(PUB / "sekoia_public_facts.csv")
    reg = json.loads((PUB / "company_register.json").read_text(encoding="utf-8"))
    rows = "".join(f"<li><b>{r.fact}:</b> {r.value} <span class='note'>({r.note}; {r.source_url.replace('https://', '')}, {r.read_on})</span></li>"
                   for r in f.itertuples() if r.fact not in ("Legal entity",))
    facts = card(f"""<h2>What Sekoia says about itself</h2><ul class="facts small">{rows}
      <li><b>Legal entity:</b> {reg['name']}, SIREN {reg['siren']}, created {reg['created']}, head office {reg['head_office_city'].title()},
      NAF {reg['naf_code']} <span class='note'>(French company register, read {reg['read_on']})</span></li></ul>""")
    job = card("""<h2>What the job asks for</h2><ul class="small">
      <li><b>Map and structure</b> Finance data: systems, sources, owners, definitions, flows; ARR, NRR, headcount, payroll cost, COGS, cash, expenses; a prioritised backlog.</li>
      <li><b>Reliable analysis</b>: documented, reusable datasets; reconciliations across accounting, billing, RevOps, HR, payroll, treasury and expenses; budget vs actual, cash, headcount plan, SaaS metrics.</li>
      <li><b>Quality and automation</b>: controls, lineage, business rules, known limits; data ready for forecasting, anomaly detection and AI; confidentiality of HR and payroll data.</li>
      <li><b>Cost side</b>: storage, compute, data retention and AI costs, gross margin. Owner of Metabase; data owner in Pigment.</li></ul>
      <p class="note">Source: careers.sekoia.com/jobs/8539454-finance-data-analyst, read 19 Nov 2026.</p>""")
    bm = h["benchmarks_latest"]
    bench = card(img(ch["bench_gm"], f"PUBLIC DATA · SEC EDGAR, form 10-K. Latest gross margin: {pct(h['bench_gm_min'])} to {pct(h['bench_gm_max'])}. Reference points, not targets for a scale-up."))
    mix = card(img(ch["bench_mix"], "PUBLIC DATA · deferred revenue = contract liabilities (current + non-current) / revenue: annual upfront billing is the norm."))
    body = f'<div class="grid2">{facts}{job}</div><div class="grid2">{bench}{mix}</div>'
    return page(1, "A fast-growing SOC platform with twelve Finance tools: the job is to make them tell one story",
                "Sekoia's public facts, the role, and what listed security vendors publish (gross margin, cost mix, upfront billing).",
                ["PUBLIC DATA"], body, "sekoia.com, careers.sekoia.com, SEC EDGAR")


def p2(h, ch):
    systems = [("CRM", "HubSpot-like", "RevOps Manager", "deals, companies"), ("Billing", "Younium-like", "billing ops", "accounts, contracts, invoices"),
               ("Accounting", "Pennylane-like", "Head of Finance", "ledger lines"), ("Treasury", "Agicap-like", "Head of Finance", "bank lines"),
               ("Planning", "Pigment-like", "Finance Data Analyst", "budget 2026"), ("HRIS", "Lucca-like", "People team", "employees"),
               ("Payroll", "SILAE-like", "People team", "payslips"), ("Expenses", "Navan-like", "Head of Finance", "expense lines"),
               ("Recruiting", "TeamTailor-like", "People team", "requisitions"), ("AWS bill", "FOCUS v1.4", "FinOps Manager", "resources, USD"),
               ("Azure bill", "FOCUS v1.4", "FinOps Manager", "resources, EUR"), ("OVHcloud bill", "FOCUS v1.4", "FinOps Manager", "resources, EUR")]
    boxes = "".join(f'<div class="sys"><b>{a}</b><span>{b}</span><span class="own">{c}</span><span class="note">{d}</span></div>' for a, b, c, d in systems)
    mapc = card(f"""<h2>Twelve systems, their owners (roles) and grain</h2><div class="sysgrid">{boxes}</div>
      <div class="flow"><span>12 exports</span>→<span>staging: one view per system</span>→<span>intermediate: customer key, contracts in annual value, 3 headcounts, cloud in EUR</span>→<span>marts: ARR, NRR, unit economics, budget, cash, reconciliations</span>→<span>Excel · dashboard · Metabase · PDF</span></div>""")
    joins = card("""<h2>Where the systems join, and where they break</h2><table class="small">
      <tr><th>Join</th><th>Key</th><th>Break found</th><th>Rule</th></tr>
      <tr><td>CRM deal → contract line</td><td>crm_deal_id</td><td>4 closed-won deals, no contract</td><td>listed to RevOps</td></tr>
      <tr><td>Billing account → customer</td><td>VAT number</td><td>12 accounts typed again at renewal</td><td>one key per VAT</td></tr>
      <tr><td>Contract → ledger</td><td>invoice id</td><td>invoices booked a month late</td><td>timing rule</td></tr>
      <tr><td>Payroll → HRIS</td><td>employee id</td><td>2 leavers still active in HRIS</td><td>headcount needs a payslip</td></tr>
      <tr><td>Cloud bill → ledger</td><td>InvoiceId</td><td>USD bills; one bill a month late</td><td>ECB rate of service month</td></tr>
      <tr><td>Cloud resource → product</td><td>Tags.product</td><td>18% of resources untagged</td><td>AI rule, then ARR share</td></tr></table>""")
    defs = card("""<h2>Definitions retained (full list: docs/METRIC_DEFINITIONS.md)</h2><table class="small">
      <tr><th>Metric</th><th>Definition</th><th>Reference source</th></tr>
      <tr><td><b>ARR</b></td><td>annual value of recurring contract lines active on the last day of the month, one customer key</td><td>billing contracts</td></tr>
      <tr><td><b>NRR / GRR</b></td><td>ARR today of last year's customers / their ARR then; GRR caps each at its old ARR</td><td>ARR above</td></tr>
      <tr><td><b>Bookings</b></td><td>annualised value signed in the period; TCV reported apart</td><td>CRM, checked vs billing</td></tr>
      <tr><td><b>Headcount</b></td><td>employment contracts at month end, interns excluded; FTE = contractual time</td><td>HRIS x payroll</td></tr>
      <tr><td><b>Payroll cost</b></td><td>gross + employer contributions, aggregated, no group &lt; 5</td><td>payroll register</td></tr>
      <tr><td><b>COGS</b></td><td>production hosting + AI inference + support &amp; SOC ops payroll + production tools</td><td>FOCUS + ledger</td></tr>
      <tr><td><b>Cash</b></td><td>bank balance, tied monthly to ledger 512000</td><td>bank</td></tr></table>""")
    body = f'<div class="g22">{mapc}<div class="stack">{joins}{defs}</div></div>'
    return page(2, "Twelve systems, one map: every Finance number has an owner, a key and a reference source",
                "Data map, lineage and the definitions that settle the arguments (SIMULATED exports inspired by the tools named in the job post).",
                ["SIMULATED"], body, "docs/DATA_MAP.md, docs/METRIC_DEFINITIONS.md")


def p3(h, ch):
    left = card(img(ch["arr_three"], "SIMULATED · ARR at each month end. CRM sums deal amounts as typed; ledger run-rate = subscription revenue x 12."))
    wf = card(img(ch["waterfall"], "SIMULATED · deal ↔ contract line on crm_deal_id; each gap classified by rule (docs/RECONCILIATIONS.md)."))
    mar = card(img(ch["march"], f"SIMULATED · 40 renewal lines: old line ends 30 March, new one starts 1 April; month-end snapshot misses them."))
    txt = card(f"""<h2>Reading</h2><ul class="small">
      <li><b>CRM +{pct(h['crm_gap_pct'])}</b>: {h['multi_year_deals_tcv']} multi-year deals carry their total contract value
      ({meur(h['tcv_effect_nov26'], 2)}); a few amounts predate the last discount ({keur(h['discount_effect_nov26'])}); {h['orphan_deals_nov26']} closed-won
      deals have no contract ({keur(h['orphan_effect_nov26'])}). Residual €0.</li>
      <li><b>False signal, March 2026</b>: raw ARR {meur(h['arr_raw_mar26'])} vs {meur(h['arr_clean_mar26'])} on contracts and in the ledger.
      Nothing was lost: a gap of 1-7 days between two lines is now read as a renewal, and a test stops any month-on-month fall above 3%.
      <b>No alert to management.</b></li>
      <li><b>Duplicates</b>: {h['billing_accounts']} billing accounts for {h['customers_all_time']} customers; on raw accounts a renewal becomes churn + new logo
      (NRR {pct(h['nrr_raw_nov26'], 1)} instead of {pct(h['nrr_clean_nov26'], 1)}). One key per VAT number fixes it.</li></ul>""", "roomy")
    body = f'<div class="grid2">{left}{wf}</div><div class="grid2">{mar}{txt}</div>'
    return page(3, f"ARR has three values; billing contracts are the reference, and the March drop was a data artefact, not churn",
                "CRM vs billing vs ledger, the CRM → billing cascade, and the one-day gap left by a billing migration.",
                ["SIMULATED"], body, "sql/marts/12_fct_arr_three_values.sql, 20_fct_arr_waterfall.sql")


def p4(h, ch):
    b = card(img(ch["bridge"], "SIMULATED · new, expansion, contraction and churn on one customer key; add-ons folded into renewals."))
    n = card(img(ch["nrr"], "SIMULATED · trailing 12 months. Dotted: same metric on the raw billing export (duplicates + migration gap)."))
    c = card(img(ch["cohort"], "SIMULATED · NRR and GRR by year of first contract."))
    t = card(f"""<h2>Reading</h2><ul class="small">
      <li>ARR {meur(h['arr_dec24'])} (Dec 2024) → <b>{meur(h['arr_nov26'])}</b> (Nov 2026), +{pct(h['arr_growth_yoy'])} year on year, {h['customers_nov26']} customers.</li>
      <li><b>NRR {pct(h['nrr_clean_nov26'], 1)}, GRR {pct(h['grr_clean_nov26'], 1)}</b>: existing customers grow; churn is low and stable.</li>
      <li>On raw data NRR swings from {pct(h['nrr_raw_feb26'], 1)} to {pct(h['nrr_raw_mar26'], 1)} in a month: the definition and the customer key
      matter more than the formula.</li>
      <li>Next step with real data: NRR by segment and plan, and bookings vs ARR timing (closed-won to contract start).</li></ul>""", "roomy")
    body = f'<div class="grid-2-1">{b}{t}</div><div class="grid-2-1">{n}{c}</div>'
    return page(4, f"Growth holds: ARR +{pct(h['arr_growth_yoy'])} a year and NRR {pct(h['nrr_clean_nov26'], 1)} once customers and contracts are reconciled",
                "ARR bridge by month, NRR and GRR over 12 months, by cohort (reference basis: billing contracts, clean).",
                ["SIMULATED"], body, "sql/marts/10_fct_arr_monthly.sql, 11_fct_nrr_cohort.sql")


def p5(h, ch):
    s = card(img(ch["ue_scatter"], f"SIMULATED usage x PUBLIC unit prices · storage + search ≈ €{h['storage_cost_per_tb_nov26']:.0f} per TB kept per month."))
    r = card(img(ch["retention"], f"SIMULATED · storage + search cost x{h['retention_storage_x']:.1f} in July 2025; -{keur(h['underwater_loss_month_nov26'])} a month in Nov 2026."))
    c = card(img(ch["cloud_mix"], f"SIMULATED · {h['untagged_resources_nov26']} of {h['resources_nov26']} resources untagged in Nov 2026 ({pct(h['untagged_cost_share_nov26'], 1)} of cost)."))
    g = card(img(ch["gm_bench"], f"SIMULATED vs PUBLIC DATA (10-K). March dips: annual bonus in support payroll. COGS here excludes customer success."))
    body = f'<div class="grid2">{s}{r}</div><div class="grid-2-1b">{c}{g}</div>'
    return page(5, f"A customer costs what it stores: three flat-fee accounts keep logs a year and lose money; AI costs need tags",
                f"Cost to serve per customer at public cloud prices; AI inference {keur(h['ai_cost_nov26'])} a month ({pct(h['ai_share_cloud_nov26'], 1)} of the cloud bill); gross margin {pct(h['gross_margin_nov26'], 1)} vs listed peers {pct(h['bench_gm_min'])}-{pct(h['bench_gm_max'])}.",
                ["SIMULATED", "PUBLIC DATA"], body, "sql/marts/14_fct_unit_economics.sql, 15_fct_gross_margin.sql, AWS / Azure / OVHcloud prices, SEC")


def p6(h, ch):
    b = card(img(ch["bva"], f"SIMULATED · budget frozen Dec 2025 vs ledger. SaaS revenue {pct(h['revenue_variance_ytd'], 1)}, costs {pct(h['opex_variance_ytd'], 1)} year to date."))
    t = card(img(ch["travel"], f"SIMULATED · €{h['sko_expenses']:,.0f} of kick-off travel incurred in January, approved in February: accrue it at close."))
    p = card(img(ch["pvf"], f"SIMULATED + PUBLIC (ECB) · USD per EUR {h['usd_rate_junaug']:.3f} → {h['usd_rate_sepnov']:.3f}; list prices unchanged."))
    hc = card(img(ch["headcount"], f"SIMULATED · Nov 2026: HRIS {h['hc_hris_active_records']}, reported {h['hc_headcount_reported']}, FTE {h['hc_fte_reported']:.1f}, paid {h['hc_paid_persons']}."))
    cash = card(f"""<h2>Cash and the close</h2><ul class="small">
      <li>Cash <b>{meur(h['cash_nov26'])}</b>; operating cash flow ≈ break-even (6-month average {keur(h['ocf_6m_avg_nov26'])}) thanks to annual upfront billing.</li>
      <li>Bank vs ledger: <b>€{h['bank_gl_diff_nov26']:,.0f}</b> (a bank fee not yet booked): WARN, fixed at the next close.</li>
      <li>Payroll vs ledger: the €{h['bonus_accrual'] / 1e3:,.0f}k bonus accrual (Dec 2025, reversed Mar 2026) explains the only gaps.</li>
      <li>Close in 5 working days (French holidays excluded): checklist in docs/MONTHLY_CLOSE_CHECKLIST.md.</li></ul>""", "auto")
    body = f'<div class="grid2x2b">{b}{t}{p}{hc}</div>{cash}'
    return page(6, "The month closes with confidence when timing, the dollar and headcount definitions are separated from real variances",
                "Budget vs actual, an expense timing effect, AWS price / volume / FX, three headcounts and the cash tie-out.",
                ["SIMULATED", "PUBLIC DATA"], body, "sql/marts/16-19, ECB, Nager.Date")


def p7(h, ch):
    tests = pd.read_csv(MARTS / "test_results.csv")
    ok = int((tests.status == "OK").sum())
    src = card("""<h2>Sources and dates</h2><table class="small">
      <tr><th>Source</th><th>Use</th><th>Read</th></tr>
      <tr><td>sekoia.com/about, careers.sekoia.com</td><td>facts "as stated by Sekoia", the role</td><td>19-20 Nov 2026</td></tr>
      <tr><td>recherche-entreprises.api.gouv.fr</td><td>legal identity only, officers not stored</td><td>19 Nov 2026</td></tr>
      <tr><td>SEC EDGAR XBRL (4 vendors, 10-K)</td><td>gross margin, R&amp;D, S&amp;M, deferred revenue</td><td>19 Nov 2026</td></tr>
      <tr><td>AWS Price List (eu-west-3), Azure Retail Prices (francecentral), OVHcloud catalog (FR)</td><td>unit prices</td><td>19 Nov 2026</td></tr>
      <tr><td>FOCUS v1.4 (FinOps Foundation, GitHub)</td><td>26 cost-export columns, all checked in the spec</td><td>19 Nov 2026</td></tr>
      <tr><td>ECB USD/EUR monthly averages</td><td>FX conversion and FX effect (Nov 2026 = Oct carried)</td><td>19 Nov 2026</td></tr>
      <tr><td>Nager.Date</td><td>French public holidays, close calendar</td><td>19 Nov 2026</td></tr></table>""")
    lim = card(f"""<h2>Assumptions and limits</h2><ul class="small">
      <li><b>No Sekoia data.</b> The company, its customers (C0001…) and employees (E0001…) are simulated (seed 42); exports are inspired by common tools, not any vendor's schema.</li>
      <li>8 data problems were planted, then found back by the checks: this shows a method, not a fact about any company.</li>
      <li>Simplified: one entity, no VAT in cash, monthly ratable revenue, a flat 10% AWS discount on list prices.</li>
      <li>Benchmarks are large listed vendors with their own COGS scope: reference points, not targets.</li>
      <li>Metabase questions run on DuckDB, not in a Metabase instance.</li></ul>
      <h2>Quality</h2><p class="small">{ok}/{len(tests)} automated tests OK (uniqueness, nulls, balanced entries, reconciliation thresholds,
      no payroll group under 5 people). The Excel pack recomputes ARR, variances, price / volume / FX and statuses by formula and audits itself.</p>""", "roomy")
    back = card("""<h2>Backlog (top 6 of 12, docs/DATA_NEEDS_BACKLOG.md)</h2><ol class="small">
      <li>One customer key across CRM, billing and usage (unique VAT in billing).</li>
      <li>Annual value field in the CRM, mandatory at closed-won.</li>
      <li>ARR / NRR / GRR from contracts in Metabase, with tests.</li>
      <li>Reconciliation pack at D+2, results in Metabase.</li>
      <li>Cloud tagging policy at deploy + allocation rule.</li>
      <li>Cost to serve per customer monthly; flag retention above contract.</li></ol>""", "roomy")
    ai = card(f"""<h2>Methods</h2><p class="small">SQL warehouse in layers (DuckDB): staging → intermediate → marts; reconciliations as cascades with thresholds;
      unit economics by cost driver; price / volume / FX split; Python for collection, simulation and outputs.</p>
      <p class="small">{AI_NOTE}</p>""", "roomy")
    body = f'<div class="grid2">{src}{lim}</div><div class="grid2">{back}{ai}</div>'
    return page(7, "Methods, limits, backlog and AI note", "What is public, what is simulated, how every number is produced, and what comes next.",
                ["OVERVIEW"], body, "README.md, docs/")


CSS = """
@page { size: 1600px 900px; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #0B0B0B; background: #F4F4F2; }
.page { width: 1600px; height: 900px; padding: 30px 44px 22px; display: flex; flex-direction: column; page-break-after: always; overflow: hidden; background: #F4F4F2; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 30px; }
h1 { font-size: 27px; margin: 0 0 6px; font-weight: 700; line-height: 1.15; max-width: 1300px; }
.sub { margin: 0; color: #52514E; font-size: 15px; max-width: 1300px; }
.tags { display: flex; gap: 6px; }
.tag { font-size: 12px; font-weight: 700; letter-spacing: .08em; padding: 5px 10px; border-radius: 4px; white-space: nowrap; color: #52514E; }
.tag-public { background: #E3EEFB; color: #1C5CAB; } .tag-simulated { background: #FBE9E0; color: #9A3B12; } .tag-overview { color: #52514E; border: 1px solid #E1E0D9; }
main { flex: 1; display: flex; flex-direction: column; gap: 12px; margin-top: 14px; min-height: 0; }
footer { display: flex; justify-content: space-between; gap: 20px; font-size: 11px; color: #898781; margin-top: 8px; }
.card { background: #FCFCFB; border: 1px solid #E1E0D9; border-radius: 8px; padding: 10px 14px; min-height: 0; overflow: hidden; }
.card h2 { font-size: 15.5px; margin: 0 0 6px; } .card h3 { font-size: 14px; margin: 0 0 4px; }
.card p, .card li { font-size: 13.5px; line-height: 1.38; margin: 3px 0; color: #2B2A27; }
.card ul, .card ol { padding-left: 18px; margin: 4px 0; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.g0 { display: grid; grid-template-columns: 1.25fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.g22 { display: grid; grid-template-columns: 1fr 1.05fr; gap: 12px; flex: 1; min-height: 0; }
.grid-2-1 { display: grid; grid-template-columns: 1.6fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid-2-1b { display: grid; grid-template-columns: 1.35fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid2x2b { display: grid; grid-template-columns: 1.35fr 1fr; grid-template-rows: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
figure { margin: 0; height: 100%; display: flex; flex-direction: column; }
figure img { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
figcaption { font-size: 11.5px; color: #52514E; margin-top: 3px; }
.tile .label { font-size: 12px; font-weight: 700; color: #52514E; letter-spacing: .04em; }
.tile .big { font-size: 36px; font-weight: 700; margin: 2px 0; color: #0B0B0B; white-space: nowrap; }
.tile p { font-size: 13px; color: #52514E; }
.stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; } .stack .card { flex: 1; }
.auto { flex: 0 0 auto !important; }
.qs li { font-size: 15px !important; margin: 6px 0; } .qs b { color: #2A78D6; margin-right: 6px; }
.pg { color: #898781; font-size: 12px; } .reco { font-size: 14px !important; margin-top: 10px !important; }
.k { color: #52514E; font-size: 12.5px; letter-spacing: .05em; margin-right: 4px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; color: #52514E; font-weight: 600; border-bottom: 1px solid #E1E0D9; padding: 3px 6px; }
td { border-bottom: 1px solid #EFEEE9; padding: 3px 6px; vertical-align: top; }
table.small td, table.small th, .small, .small li { font-size: 12.5px !important; }
.note { font-size: 11.5px !important; color: #6B6A65 !important; }
.facts li { margin: 4px 0; }
.sysgrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 6px 0 10px; }
.sys { border: 1px solid #E1E0D9; border-radius: 6px; padding: 7px 9px; display: flex; flex-direction: column; gap: 1px; background: #fff; }
.sys b { font-size: 14px; color: #2A78D6; } .sys span { font-size: 12px; color: #2B2A27; } .sys .own { font-weight: 600; color: #52514E; }
.flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 13px; color: #52514E; margin-top: 8px; }
.roomy p, .roomy li, .roomy .small, .roomy .small li { font-size: 15px !important; line-height: 1.45; }
.roomy .qs li { font-size: 17px !important; margin: 9px 0; }
.flow span { background: #EEF4FC; color: #1C5CAB; border-radius: 5px; padding: 6px 8px; font-size: 12.5px; }
"""


def build_html():
    ch = charts.build_all()
    h = json.loads((MARTS / "headline.json").read_text(encoding="utf-8"))
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Sekoia - Finance data case study</title><style>{CSS}</style></head><body>
{''.join(p(h, ch) for p in (p0, p1, p2, p3, p4, p5, p6, p7))}
</body></html>"""
    out = REP / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def find_browser():
    for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", shutil.which("msedge") or "", shutil.which("google-chrome") or "",
              shutil.which("chromium") or ""]:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("Edge or Chrome is needed to print the PDF")


def print_pdf(html):
    pdf, tmp = REP / PDF_NAME, REP / "_print.pdf"
    profile = tempfile.mkdtemp()            # own profile: an open Edge window would otherwise take the call
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000", f"--print-to-pdf={tmp}", html.as_uri()],
                   check=True, timeout=180)
    last = -1
    for _ in range(120):                    # Edge can return before its child process has written the file
        time.sleep(1)
        size = tmp.stat().st_size if tmp.exists() else -1
        if size > 0 and size == last:
            break
        last = size
    shutil.rmtree(profile, ignore_errors=True)
    reader, writer = PdfReader(str(tmp)), PdfWriter()       # rewrite with neutral metadata
    for pg in reader.pages:
        writer.add_page(pg)
    writer.add_metadata({"/Title": "Sekoia - Finance data case study", "/Author": "", "/Creator": "", "/Producer": ""})
    with open(pdf, "wb") as fh:
        writer.write(fh)
    tmp.unlink()
    return pdf


def main():
    html = build_html()
    pdf = print_pdf(html)
    print("written", pdf.relative_to(ROOT), len(PdfReader(str(pdf)).pages), "pages")


if __name__ == "__main__":
    main()
