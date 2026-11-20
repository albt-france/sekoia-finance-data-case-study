"""Self-contained interactive dashboard (one HTML file, Plotly embedded, works offline): dashboard/finance_data_dashboard.html

Tabs: (1) ARR & NRR, (2) Unit economics & cloud costs, (3) Headcount & payroll (aggregated), (4) Budget vs actual & cash,
(5) Data quality (reconciliations and test status). Every number is read from data/marts.
    python src/build_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
OUT = ROOT / "dashboard" / "finance_data_dashboard.html"


def rec(name, query=None, cols=None):
    d = pd.read_csv(MARTS / f"{name}.csv")
    if query:
        d = d.query(query)
    if cols:
        d = d[cols]
    return json.loads(d.round(4).to_json(orient="records"))


def data():
    h = json.loads((MARTS / "headline.json").read_text(encoding="utf-8"))
    ue = pd.read_csv(MARTS / "fct_unit_economics.csv")
    last = ue.month.max()
    cloud = pd.read_csv(ROOT / "data" / "sim" / "cloud_costs_focus.csv")
    return {
        "h": h,
        "bench": h["benchmarks_latest"],
        "three": rec("fct_arr_three_values"),
        "bridge": rec("fct_arr_monthly"),
        "nrr": rec("fct_nrr_cohort"),
        "gm": rec("fct_gross_margin"),
        "ue": rec("fct_unit_economics", f"month == '{last}'", ["customer_key", "segment", "plan_type", "retention_days", "stored_tb",
                                                                 "arr_eur", "revenue_month_eur", "cogs_eur", "gross_margin_eur", "gross_margin_pct"]),
        "pvf": rec("fct_cloud_price_volume_fx"),
        "hc": rec("fct_headcount_payroll"),
        "bva": rec("fct_budget_vs_actual"),
        "cash": rec("fct_cash"),
        "recon": rec("fct_reconciliations", cols=["month", "check_name", "diff", "residual", "status", "explanation"]),
        "tests": rec("test_results"),
        "wf": rec("fct_arr_waterfall"),
        "untagged": json.loads(cloud.assign(untagged=cloud.Tags == "{}").groupby("ChargePeriodStart").untagged.mean().round(4).to_json()),
    }


HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Finance data dashboard</title>
<style>
:root { color-scheme: light; --bg:#F4F4F2; --card:#FCFCFB; --line:#E1E0D9; --ink:#0B0B0B; --muted:#52514E; --accent:#2A78D6; --pub:#E3EEFB; --pubt:#1C5CAB; --sim:#FBE9E0; --simt:#9A3B12; --ok:#1BAF7A; --warn:#EDA100; --ko:#D03B3B; --exp:#86B6EF; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; --bg:#141413; --card:#1A1A19; --line:#33322F; --ink:#F0EFEC; --muted:#C3C2B7; --accent:#3987E5; --pub:#1C2E45; --pubt:#9CC3F2; --sim:#40261A; --simt:#F2B89C; } }
:root[data-theme="dark"] { color-scheme: dark; --bg:#141413; --card:#1A1A19; --line:#33322F; --ink:#F0EFEC; --muted:#C3C2B7; --accent:#3987E5; --pub:#1C2E45; --pubt:#9CC3F2; --sim:#40261A; --simt:#F2B89C; }
* { box-sizing: border-box; }
body { margin:0; font-family:'Segoe UI', Arial, sans-serif; background:var(--bg); color:var(--ink); }
.wrap { max-width:1280px; margin:0 auto; padding:20px 16px 40px; }
h1 { font-size:24px; margin:0 0 4px; } .sub { color:var(--muted); margin:0 0 14px; font-size:14px; }
nav { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
nav button { border:1px solid var(--line); background:var(--card); color:var(--ink); padding:7px 12px; border-radius:6px; cursor:pointer; font:inherit; font-size:14px; }
nav button.on { border-color:var(--accent); color:var(--accent); font-weight:600; }
.tab { display:none; } .tab.on { display:block; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:12px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-bottom:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; min-width:0; }
.card h2 { font-size:15px; margin:0 0 6px; } .card p { font-size:13px; color:var(--muted); margin:4px 0; }
.tag { font-size:11px; font-weight:700; letter-spacing:.06em; padding:3px 7px; border-radius:4px; margin-left:6px; vertical-align:middle; }
.pub { background:var(--pub); color:var(--pubt); } .sim { background:var(--sim); color:var(--simt); }
.ctrl { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin:6px 0 10px; font-size:13px; color:var(--muted); }
select { font:inherit; font-size:13px; padding:4px 6px; border:1px solid var(--line); border-radius:5px; background:var(--card); color:var(--ink); }
.big { font-size:28px; font-weight:700; color:var(--ink); margin:2px 0; } .lab { font-size:12px; color:var(--muted); font-weight:600; }
table { border-collapse:collapse; width:100%; font-size:13px; } th, td { text-align:left; padding:4px 6px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; } .scroll { max-height:340px; overflow:auto; }
footer { margin-top:18px; font-size:12px; color:var(--muted); }
.plot { width:100%; height:330px; }
.st { font-weight:700; } .st-OK { color:var(--ok); } .st-EXPLAINED { color:var(--accent); } .st-WARN { color:var(--warn); } .st-KO { color:var(--ko); }
</style></head><body><div class="wrap">
<h1>Finance data: one set of numbers everyone can trust</h1>
<p class="sub">Companion dashboard to the case study. A <b>fictional</b> 180-person cybersecurity SaaS scale-up, 24 months (Dec 2024 - Nov 2026). Business data SIMULATED (not Sekoia's numbers); public data tagged.</p>
<nav id="nav"><button data-t="t1" class="on">ARR &amp; NRR</button><button data-t="t2">Unit economics &amp; cloud costs</button><button data-t="t3">Headcount &amp; payroll</button><button data-t="t4">Budget vs actual &amp; cash</button><button data-t="t5">Data quality</button></nav>

<section id="t1" class="tab on">
 <div class="kpis" id="k1"></div>
 <div class="grid">
  <div class="card"><h2>One month, four "ARR" <span class="tag sim">SIMULATED</span></h2><div id="c_three" class="plot"></div><p>Reference = billing contracts, clean. The raw export drops in March 2026 (billing migration): the ledger does not.</p></div>
  <div class="card"><h2>ARR bridge by month <span class="tag sim">SIMULATED</span></h2><div class="ctrl">Basis <select id="basis"><option>contracts (clean)</option><option>billing raw (by account)</option></select></div><div id="c_bridge" class="plot" style="height:300px"></div></div>
  <div class="card"><h2>NRR and GRR, trailing 12 months <span class="tag sim">SIMULATED</span></h2><div id="c_nrr" class="plot"></div><p>Dotted = same metric on the raw billing export (duplicates + migration gap).</p></div>
  <div class="card"><h2>NRR by cohort, latest month <span class="tag sim">SIMULATED</span></h2><div id="t_cohort"></div></div>
 </div>
</section>

<section id="t2" class="tab">
 <div class="kpis" id="k2"></div>
 <div class="grid">
  <div class="card"><h2>Gross margin vs listed security vendors <span class="tag sim">SIMULATED</span><span class="tag pub">PUBLIC DATA</span></h2><div id="c_gm" class="plot"></div><p>Band = range of the latest 10-K gross margins (CrowdStrike, Rapid7, SentinelOne, Tenable; SEC EDGAR). Benchmarks, not targets.</p></div>
  <div class="card"><h2>Customers: stored TB vs gross margin <span class="tag sim">SIMULATED</span></h2><div class="ctrl">Segment <select id="seg"><option>All</option></select></div><div id="c_ue" class="plot" style="height:300px"></div><p>Red = below zero. Costs at public AWS / Azure / OVHcloud unit prices.</p></div>
  <div class="card"><h2>AWS bill: price, volume, FX <span class="tag sim">SIMULATED</span><span class="tag pub">ECB FX</span></h2><div class="ctrl">Comparison <select id="pvf"></select></div><div id="c_pvf" class="plot" style="height:300px"></div></div>
  <div class="card"><h2>AI cost and untagged resources <span class="tag sim">SIMULATED</span></h2><div id="c_ai" class="plot"></div><p>AI feature launched Oct 2025. Untagged resources cannot be allocated to a product without a rule.</p></div>
 </div>
 <div class="card" style="margin-top:12px"><h2>Customers with the lowest margin, latest month <span class="tag sim">SIMULATED</span></h2><div id="t_ue" class="scroll"></div></div>
</section>

<section id="t3" class="tab">
 <div class="kpis" id="k3"></div>
 <div class="grid">
  <div class="card"><h2>Three headcounts, all "right" <span class="tag sim">SIMULATED</span></h2><div id="c_hc" class="plot"></div><p>Reported = employment contracts at month end, interns and HRIS records without payslip excluded.</p></div>
  <div class="card"><h2>Payroll cost by department, latest month <span class="tag sim">SIMULATED</span></h2><div id="c_pay" class="plot"></div><p>Aggregated. Groups under 5 people are blanked (none here). Gross + employer contributions.</p></div>
 </div>
</section>

<section id="t4" class="tab">
 <div class="kpis" id="k4"></div>
 <div class="grid">
  <div class="card"><h2>Variance to budget, year to date <span class="tag sim">SIMULATED</span></h2><div id="c_var" class="plot" style="height:420px"></div><p>Green = favorable (revenue above, cost below budget).</p></div>
  <div class="card"><h2>Budget vs actual by month <span class="tag sim">SIMULATED</span></h2><div class="ctrl">Line <select id="line"></select></div><div id="c_line" class="plot" style="height:300px"></div></div>
  <div class="card"><h2>Cash and operating cash flow <span class="tag sim">SIMULATED</span></h2><div id="c_cash" class="plot"></div><p>Annual upfront billing keeps operating cash flow near zero although the P&amp;L is close to break-even.</p></div>
 </div>
</section>

<section id="t5" class="tab">
 <div class="kpis" id="k5"></div>
 <div class="grid">
  <div class="card"><h2>Reconciliation status, every check, every month <span class="tag sim">SIMULATED</span></h2><div id="c_recon" class="plot" style="height:300px"></div><p>OK / EXPLAINED / WARN / KO. Hover for the difference and its explanation.</p></div>
  <div class="card"><h2>From CRM to billing ARR <span class="tag sim">SIMULATED</span></h2><div class="ctrl">Month <select id="wfm"></select></div><div id="c_wf" class="plot" style="height:300px"></div></div>
 </div>
 <div class="grid" style="margin-top:12px">
  <div class="card"><h2>Open differences (latest month)</h2><div id="t_recon"></div></div>
  <div class="card"><h2>Data tests of the last build</h2><div id="t_tests" class="scroll"></div></div>
 </div>
</section>
<footer>Independent case study based on public data · not affiliated with or endorsed by Sekoia. Simulated exports are inspired by common tools; they are not any vendor's schema. Public data: SEC EDGAR, ECB, AWS / Azure / OVHcloud public prices, FOCUS v1.4.</footer>
</div>
<script>__PLOTLY__</script>
<script>
const D = __DATA__, H = D.h;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const lay = (x) => Object.assign({margin:{l:60,r:16,t:10,b:40}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{family:'Segoe UI, Arial', size:12, color:css('--muted')}, xaxis:{gridcolor:css('--line'), zeroline:false},
  yaxis:{gridcolor:css('--line'), zeroline:false}, legend:{orientation:'h', y:1.14}, hoverlabel:{font:{family:'Segoe UI'}}}, x||{});
const cfg = {displayModeBar:false, responsive:true};
const M = s => s.slice(0,7), eur = v => '€' + Math.round(v).toLocaleString('en'), meur = v => '€' + (v/1e6).toFixed(1) + 'M', pct = (v,d=1) => (v*100).toFixed(d) + '%';
const C = {blue:'#2A78D6', grey:'#A3A19A', red:'#D03B3B', orange:'#EB6834', aqua:'#1BAF7A', yellow:'#EDA100', pink:'#E87BA4'};
const kpi = (el, items) => document.getElementById(el).innerHTML = items.map(i => `<div class="card"><div class="lab">${i[0]}</div><div class="big">${i[1]}</div><p>${i[2]}</p></div>`).join('');
const table = (el, cols, rows) => document.getElementById(el).innerHTML = '<table><tr>' + cols.map(c=>'<th>'+c[0]+'</th>').join('') + '</tr>' + rows.map(r=>'<tr>'+cols.map(c=>'<td>'+c[1](r)+'</td>').join('')+'</tr>').join('') + '</table>';
document.querySelectorAll('#nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#nav button').forEach(x=>x.classList.toggle('on', x===b));
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.id===b.dataset.t));
  document.querySelectorAll('#'+b.dataset.t+' .js-plotly-plot').forEach(el => Plotly.Plots.resize(el));
});

// ---- tab 1
kpi('k1', [['ARR, Nov 2026 (billing contracts)', meur(H.arr_nov26), '+' + pct(H.arr_growth_yoy,0) + ' year on year, ' + H.customers_nov26 + ' customers'],
  ['NRR 12m / GRR 12m', pct(H.nrr_clean_nov26) + ' / ' + pct(H.grr_clean_nov26), 'raw billing export: ' + pct(H.nrr_raw_nov26) + ' (duplicate accounts)'],
  ['CRM "ARR" as typed', meur(H.crm_arr_nov26), '+' + pct(H.crm_gap_pct,0) + ' vs billing: ' + H.multi_year_deals_tcv + ' multi-year deals typed at TCV'],
  ['March 2026 false signal', 'NRR ' + pct(H.nrr_raw_mar26,0), 'raw export only; contracts say ' + pct(H.nrr_clean_mar26,0) + '. Not escalated.']]);
const T = D.three, x3 = T.map(r=>M(r.month));
Plotly.newPlot('c_three', [
  {x:x3, y:T.map(r=>r.arr_crm_as_typed), name:'CRM as typed', mode:'lines', line:{color:C.grey, dash:'dot'}},
  {x:x3, y:T.map(r=>r.arr_billing_raw), name:'Billing raw export', mode:'lines', line:{color:C.orange}},
  {x:x3, y:T.map(r=>r.arr_gl_runrate), name:'Ledger run-rate', mode:'lines', line:{color:C.aqua, dash:'dash'}},
  {x:x3, y:T.map(r=>r.arr_billing_clean), name:'Billing contracts, clean', mode:'lines', line:{color:C.blue, width:3}}],
  lay({yaxis:{tickprefix:'€', gridcolor:css('--line')}, hovermode:'x unified'}), cfg);
function bridge() {
  const b = document.getElementById('basis').value, r = D.bridge.filter(x=>x.basis===b), x = r.map(z=>M(z.month));
  Plotly.react('c_bridge', [
    {type:'bar', x, y:r.map(z=>z.new_arr), name:'New', marker:{color:C.blue}}, {type:'bar', x, y:r.map(z=>z.expansion_arr), name:'Expansion', marker:{color:C.aqua}},
    {type:'bar', x, y:r.map(z=>z.contraction_arr), name:'Contraction', marker:{color:C.yellow}}, {type:'bar', x, y:r.map(z=>z.churned_arr), name:'Churn', marker:{color:C.red}}],
    lay({barmode:'relative', yaxis:{tickprefix:'€', gridcolor:css('--line')}}), cfg);
}
document.getElementById('basis').onchange = bridge; bridge();
const N = D.nrr.filter(r=>r.cohort==='All'), nc = N.filter(r=>r.basis==='contracts (clean)'), nr = N.filter(r=>r.basis!=='contracts (clean)');
Plotly.newPlot('c_nrr', [
  {x:nc.map(r=>M(r.month)), y:nc.map(r=>r.nrr), name:'NRR', mode:'lines+markers', line:{color:C.blue, width:3}},
  {x:nc.map(r=>M(r.month)), y:nc.map(r=>r.grr), name:'GRR', mode:'lines+markers', line:{color:C.aqua}},
  {x:nr.map(r=>M(r.month)), y:nr.map(r=>r.nrr), name:'NRR raw export', mode:'lines', line:{color:C.orange, dash:'dot'}}],
  lay({yaxis:{tickformat:'.0%', gridcolor:css('--line')}, shapes:[{type:'line', xref:'paper', x0:0, x1:1, y0:1, y1:1, line:{color:C.grey, dash:'dash', width:1}}]}), cfg);
const lastN = nc[nc.length-1].month;
table('t_cohort', [['Cohort (first contract)', r=>r.cohort], ['Customers', r=>r.customers_base], ['ARR 12m ago', r=>eur(r.arr_base)], ['ARR now', r=>eur(r.arr_now)], ['NRR', r=>pct(r.nrr)], ['GRR', r=>pct(r.grr)]],
  D.nrr.filter(r=>r.month===lastN && r.basis==='contracts (clean)'));

// ---- tab 2
kpi('k2', [['Gross margin, Nov 2026', pct(H.gross_margin_nov26), 'listed peers (10-K): ' + pct(H.bench_gm_min,0) + ' - ' + pct(H.bench_gm_max,0)],
  ['Customers below zero margin', H.underwater_customers_nov26, 'flat fee, retention 120 → 365 days; ' + eur(H.underwater_loss_month_nov26) + ' lost a month'],
  ['AI inference, Nov 2026', eur(H.ai_cost_nov26), pct(H.ai_share_cloud_nov26) + ' of the cloud bill'],
  ['Untagged cloud resources', pct(H.untagged_resource_share_nov26,0), H.untagged_resources_nov26 + ' of ' + H.resources_nov26 + ' resources; ' + pct(H.untagged_cost_share_nov26) + ' of cost']]);
const G = D.gm.filter(r=>r.gross_margin_pct!==null), xg = G.map(r=>M(r.month));
Plotly.newPlot('c_gm', [
  {x:xg.concat(xg.slice().reverse()), y:xg.map(()=>H.bench_gm_max).concat(xg.map(()=>H.bench_gm_min)), fill:'toself', fillcolor:'rgba(163,161,154,0.25)', line:{width:0}, name:'Listed peers (10-K range)', hoverinfo:'skip'},
  {x:xg, y:G.map(r=>r.gross_margin_pct), name:'Gross margin', mode:'lines+markers', line:{color:C.blue, width:3}},
  {x:xg, y:G.map(r=>r.cloud_pct_revenue), name:'Cloud + AI, % revenue', mode:'lines', line:{color:C.orange}}],
  lay({yaxis:{tickformat:'.0%', gridcolor:css('--line')}}), cfg);
[...new Set(D.ue.map(r=>r.segment))].forEach(s => document.getElementById('seg').insertAdjacentHTML('beforeend', `<option>${s}</option>`));
function ue() {
  const s = document.getElementById('seg').value, r = D.ue.filter(x=>s==='All' || x.segment===s);
  Plotly.react('c_ue', [{type:'scatter', mode:'markers', x:r.map(z=>z.stored_tb), y:r.map(z=>z.gross_margin_pct), text:r.map(z=>z.customer_key+' · '+z.segment+' · '+z.plan_type+' · '+z.retention_days+' days'),
    marker:{size:r.map(z=>6+Math.sqrt(z.arr_eur)/40), color:r.map(z=>z.gross_margin_eur<0?C.red:C.blue), opacity:0.7}, hovertemplate:'%{text}<br>stored %{x:.0f} TB · margin %{y:.0%}<extra></extra>'}],
    lay({xaxis:{type:'log', title:'TB stored (log)', gridcolor:css('--line')}, yaxis:{tickformat:'.0%', gridcolor:css('--line')}, showlegend:false,
      shapes:[{type:'line', xref:'paper', x0:0, x1:1, y0:0, y1:0, line:{color:C.red, dash:'dash', width:1}}]}), cfg);
}
document.getElementById('seg').onchange = ue; ue();
const P = D.pvf; P.forEach((r,i) => document.getElementById('pvf').insertAdjacentHTML('beforeend', `<option value="${i}">${r.comparison==='actual vs budget' ? M(r.month)+' vs budget' : r.comparison}</option>`));
document.getElementById('pvf').value = P.findIndex(r=>r.comparison!=='actual vs budget');
function pvf() {
  const r = P[+document.getElementById('pvf').value];
  Plotly.react('c_pvf', [{type:'waterfall', x:['Base','Volume','Price (discount)','FX (USD)','Actual'], measure:['absolute','relative','relative','relative','total'],
    y:[r.base_eur, r.volume_effect_eur, r.price_effect_eur, r.fx_effect_eur, r.actual_eur], text:[eur(r.base_eur), eur(r.volume_effect_eur), eur(r.price_effect_eur), eur(r.fx_effect_eur), eur(r.actual_eur)],
    textposition:'outside', increasing:{marker:{color:C.red}}, decreasing:{marker:{color:C.aqua}}, totals:{marker:{color:C.blue}}, connector:{line:{color:css('--line')}}}],
    lay({yaxis:{tickprefix:'€', gridcolor:css('--line'), range:[Math.min(r.base_eur, r.actual_eur)*0.9, Math.max(r.base_eur, r.actual_eur)*1.06]}, showlegend:false}), cfg);
}
document.getElementById('pvf').onchange = pvf; pvf();
const U = Object.entries(D.untagged).sort();
Plotly.newPlot('c_ai', [
  {type:'bar', x:xg, y:G.map(r=>r.ai_inference_eur), name:'AI inference (EUR)', marker:{color:C.pink}},
  {x:U.map(r=>M(r[0])), y:U.map(r=>r[1]), name:'Untagged resources (share)', yaxis:'y2', mode:'lines+markers', line:{color:C.red}}],
  lay({yaxis:{tickprefix:'€', gridcolor:css('--line')}, yaxis2:{overlaying:'y', side:'right', tickformat:'.0%', range:[0,0.3], showgrid:false}}), cfg);
table('t_ue', [['Customer', r=>r.customer_key], ['Segment', r=>r.segment], ['Plan', r=>r.plan_type], ['Retention', r=>r.retention_days+' d'], ['Stored TB', r=>r.stored_tb.toFixed(0)],
  ['Revenue / month', r=>eur(r.revenue_month_eur)], ['COGS / month', r=>eur(r.cogs_eur)], ['Margin', r=>'<span style="color:'+(r.gross_margin_eur<0?C.red:'inherit')+'">'+pct(r.gross_margin_pct,0)+'</span>']],
  D.ue.slice().sort((a,b)=>a.gross_margin_pct-b.gross_margin_pct).slice(0,12));

// ---- tab 3
const HC = D.hc.filter(r=>r.department==='All departments'), xh = HC.map(r=>M(r.month));
kpi('k3', [['Reported headcount, Nov 2026', H.hc_headcount_reported, 'employment contracts at month end'], ['FTE', H.hc_fte_reported.toFixed(1), 'part-time counted at contractual %'],
  ['HRIS active records', H.hc_hris_active_records, H.hc_interns + ' interns + ' + H.hc_suspected_leavers + ' leavers without end date'], ['Paid persons', H.hc_paid_persons, 'incl. interns\\' stipend and final settlements']]);
Plotly.newPlot('c_hc', [
  {x:xh, y:HC.map(r=>r.hris_active_records), name:'HRIS active records', mode:'lines', line:{color:C.grey}},
  {x:xh, y:HC.map(r=>r.paid_persons), name:'Paid persons', mode:'lines', line:{color:C.orange, dash:'dot'}},
  {x:xh, y:HC.map(r=>r.headcount_reported), name:'Reported headcount', mode:'lines', line:{color:C.blue, width:3}},
  {x:xh, y:HC.map(r=>r.fte_reported), name:'FTE', mode:'lines', line:{color:C.aqua, dash:'dash'}}], lay({hovermode:'x unified'}), cfg);
const lastH = HC[HC.length-1].month, dep = D.hc.filter(r=>r.month===lastH && r.department!=='All departments' && !r.suppressed_small_group).sort((a,b)=>a.payroll_cost_eur-b.payroll_cost_eur);
Plotly.newPlot('c_pay', [{type:'bar', orientation:'h', y:dep.map(r=>r.department), x:dep.map(r=>r.payroll_cost_eur), marker:{color:C.blue}, text:dep.map(r=>r.headcount_reported+' people'), textposition:'auto',
  hovertemplate:'%{y}: €%{x:,.0f}<extra></extra>'}], lay({margin:{l:170,r:16,t:10,b:40}, xaxis:{tickprefix:'€', gridcolor:css('--line')}, showlegend:false}), cfg);

// ---- tab 4
kpi('k4', [['SaaS revenue vs budget, YTD', pct(H.revenue_variance_ytd), 'Jan - Nov 2026'], ['Costs vs budget, YTD', pct(H.opex_variance_ytd), 'negative = below budget'],
  ['Travel, Jan → Feb 2026', pct(H.travel_jan26[2],0) + ' → +' + pct(H.travel_feb26[2],0), 'sales kick-off claimed a month late: timing, not overspend'], ['Cash, Nov 2026', meur(H.cash_nov26), 'operating cash flow ~ break-even (6-month avg ' + eur(H.ocf_6m_avg_nov26) + ')']]);
const lines = [...new Set(D.bva.map(r=>r.budget_line))];
const ytd = lines.map(l => { const r = D.bva.filter(x=>x.budget_line===l); const b = r.reduce((a,x)=>a+x.budget_eur,0), a = r.reduce((s,x)=>s+x.actual_eur,0);
  return {l, v:a-b, fav: r[0].line_group==='Revenue' ? a>=b : a<=b}; }).sort((a,b)=>Math.abs(a.v)-Math.abs(b.v));
Plotly.newPlot('c_var', [{type:'bar', orientation:'h', y:ytd.map(r=>r.l), x:ytd.map(r=>r.v), marker:{color:ytd.map(r=>r.fav?C.aqua:C.red)}, hovertemplate:'%{y}: €%{x:,.0f}<extra></extra>'}],
  lay({margin:{l:230,r:16,t:10,b:40}, xaxis:{tickprefix:'€', gridcolor:css('--line')}, showlegend:false}), cfg);
lines.forEach(l => document.getElementById('line').insertAdjacentHTML('beforeend', `<option>${l}</option>`));
document.getElementById('line').value = 'Travel and expenses';
function line() { const r = D.bva.filter(x=>x.budget_line===document.getElementById('line').value), x = r.map(z=>M(z.month));
  Plotly.react('c_line', [{type:'bar', x, y:r.map(z=>z.budget_eur), name:'Budget', marker:{color:C.grey}}, {type:'bar', x, y:r.map(z=>z.actual_eur), name:'Actual', marker:{color:C.blue}}],
    lay({barmode:'group', yaxis:{tickprefix:'€', gridcolor:css('--line')}}), cfg); }
document.getElementById('line').onchange = line; line();
const CA = D.cash;
Plotly.newPlot('c_cash', [{type:'bar', x:CA.map(r=>M(r.month)), y:CA.map(r=>r.operating_cash_flow), name:'Operating cash flow', marker:{color:CA.map(r=>r.operating_cash_flow<0?C.red:C.aqua)}},
  {x:CA.map(r=>M(r.month)), y:CA.map(r=>r.closing_cash), name:'Closing cash', yaxis:'y2', mode:'lines', line:{color:C.blue, width:3}}],
  lay({yaxis:{tickprefix:'€', gridcolor:css('--line')}, yaxis2:{overlaying:'y', side:'right', tickprefix:'€', showgrid:false, rangemode:'tozero'}}), cfg);

// ---- tab 5
const R = D.recon, checks = [...new Set(R.map(r=>r.check_name))], months = [...new Set(R.map(r=>M(r.month)))];
const sv = {OK:0, EXPLAINED:1, WARN:2, KO:3};
const okTests = D.tests.filter(t=>t.status==='OK').length;
kpi('k5', [['Data tests', okTests + ' / ' + D.tests.length, 'uniqueness, nulls, balances, thresholds, confidentiality'],
  ['Reconciliation checks', checks.length + ' × ' + months.length + ' months', (H.recon_status_KO||0) + ' KO'],
  ['Explained differences', R.filter(r=>r.status==='EXPLAINED').length, 'documented items (TCV, cut-off, accrual, HRIS)'],
  ['Open warnings', R.filter(r=>r.status==='WARN').length, 'bank fee not yet booked']]);
const z = checks.map(c => months.map(m => { const r = R.find(x=>x.check_name===c && M(x.month)===m); return r ? sv[r.status] : null; }));
const tx = checks.map(c => months.map(m => { const r = R.find(x=>x.check_name===c && M(x.month)===m); return r ? r.status + ' · diff ' + Math.round(r.diff).toLocaleString('en') + (r.explanation ? '<br>' + r.explanation : '') : ''; }));
Plotly.newPlot('c_recon', [{type:'heatmap', z, x:months, y:checks, text:tx, hovertemplate:'%{y} · %{x}<br>%{text}<extra></extra>', zmin:0, zmax:3, showscale:false,
  colorscale:[[0,'#1BAF7A'],[0.33,'#1BAF7A'],[0.34,'#86B6EF'],[0.6,'#86B6EF'],[0.61,'#EDA100'],[0.85,'#EDA100'],[0.86,'#D03B3B'],[1,'#D03B3B']], xgap:2, ygap:2}],
  lay({margin:{l:250,r:10,t:10,b:50}, yaxis:{autorange:'reversed'}}), cfg);
const W = D.wf, wm = [...new Set(W.map(r=>M(r.month)))];
wm.forEach(m => document.getElementById('wfm').insertAdjacentHTML('beforeend', `<option>${m}</option>`));
document.getElementById('wfm').value = '2026-03';
function wf() { const r = W.filter(x=>M(x.month)===document.getElementById('wfm').value && x.step_order<=8);
  Plotly.react('c_wf', [{type:'waterfall', orientation:'h', y:r.map(z=>z.step), x:r.map(z=>z.amount_eur), measure:r.map(z=>[1,6,8].includes(z.step_order)?'absolute':'relative'),
    text:r.map(z=>meur(z.amount_eur)), textposition:'auto', increasing:{marker:{color:C.aqua}}, decreasing:{marker:{color:C.red}}, totals:{marker:{color:C.blue}}, connector:{line:{color:css('--line')}}}],
    lay({margin:{l:330,r:16,t:10,b:40}, yaxis:{autorange:'reversed'}, xaxis:{tickprefix:'€', gridcolor:css('--line')}, showlegend:false}), cfg); }
document.getElementById('wfm').onchange = wf; wf();
const lastR = R.reduce((a,r)=>r.month>a?r.month:a,'');
table('t_recon', [['Check', r=>r.check_name], ['Difference', r=>Math.round(r.diff).toLocaleString('en')], ['Status', r=>'<span class="st st-'+r.status+'">'+r.status+'</span>'], ['Why', r=>r.explanation||'']],
  R.filter(r=>r.month===lastR));
table('t_tests', [['Test', r=>r.test], ['Status', r=>'<span class="st st-'+(r.status==='OK'?'OK':'KO')+'">'+r.status+'</span>']], D.tests);
</script></body></html>"""


def main():
    d = data()
    d["h"]["recon_status_KO"] = json.loads((MARTS / "headline.json").read_text(encoding="utf-8"))["recon_status"].get("KO", 0)
    html = HTML.replace("__PLOTLY__", get_plotlyjs()).replace("__DATA__", json.dumps(d))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("written", OUT.relative_to(ROOT), f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
