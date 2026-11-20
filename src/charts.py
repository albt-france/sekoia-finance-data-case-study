"""Matplotlib charts for the PDF report (report/img/*.png). Every number is read from data/marts or data/public.

Style of the earlier case studies: light grey-beige page, white cards, blue for the reference data, grey for comparisons,
red for alerts and thresholds, dashed lines for thresholds, Segoe UI.
"""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARTS, PUB = ROOT / "data" / "marts", ROOT / "data" / "public"
IMG = ROOT / "report" / "img"
IMG.mkdir(parents=True, exist_ok=True)

BLUE, GREY, RED, ORANGE, AQUA, YELLOW, PINK = "#2A78D6", "#A3A19A", "#D03B3B", "#EB6834", "#1BAF7A", "#EDA100", "#E87BA4"
INK, MUTED, GRID = "#0B0B0B", "#52514E", "#E1E0D9"
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "figure.facecolor": "white", "axes.facecolor": "white", "legend.frameon": False,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
})


def m(name):
    d = pd.read_csv(MARTS / f"{name}.csv")
    if "month" in d:
        d["month"] = pd.to_datetime(d["month"])
    return d


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / f"{name}.png", dpi=200)
    plt.close(fig)
    return f"img/{name}.png"


meur = mtick.FuncFormatter(lambda x, _: f"€{x / 1e6:,.0f}M" if abs(x) >= 1e6 else f"€{x / 1e3:,.0f}k")
keur = mtick.FuncFormatter(lambda x, _: f"€{x / 1e3:,.0f}k")
mfmt = lambda ax: ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))


def bench_gm():
    b = pd.read_csv(PUB / "sec_benchmarks.csv", parse_dates=["period_end"])
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    for (co, g), c in zip(b.groupby("company"), [BLUE, ORANGE, AQUA, YELLOW]):
        ax.plot(g.period_end, g.gross_margin, marker="o", color=c, lw=2, label=co)
        ax.annotate(f"{g.gross_margin.iloc[-1]:.0%}", (g.period_end.iloc[-1], g.gross_margin.iloc[-1]), xytext=(4, -3), textcoords="offset points", fontsize=8, color=c)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    ax.set_ylim(0.55, 0.85)
    ax.set_title("Gross margin, fiscal years (10-K)")
    ax.legend(ncol=2, fontsize=8, loc="lower right")
    return save(fig, "bench_gm")


def bench_mix():
    b = pd.read_csv(PUB / "sec_benchmarks.csv", parse_dates=["period_end"]).sort_values("period_end").groupby("company").tail(1)
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    x = np.arange(len(b))
    for k, (col, lab, c) in enumerate([("rnd_pct_revenue", "R&D", BLUE), ("sm_pct_revenue", "Sales & marketing", GREY), ("deferred_rev_pct_revenue", "Deferred revenue", ORANGE)]):
        ax.bar(x + (k - 1) * 0.26, b[col], 0.26, color=c, label=lab)
    ax.set_xticks(x, [f"{c}\nFY {p:%b %Y}" for c, p in zip(b.company, b.period_end)], fontsize=8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    ax.set_title("As % of revenue, latest 10-K")
    ax.legend(fontsize=8, ncol=3, loc="upper left")
    return save(fig, "bench_mix")


def arr_three():
    t = m("fct_arr_three_values")
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(t.month, t.arr_crm_as_typed, ":", color=GREY, lw=2, label="CRM, amounts as typed")
    ax.plot(t.month, t.arr_billing_raw, color=ORANGE, lw=1.6, label="Billing, raw export")
    ax.plot(t.month, t.arr_gl_runrate, "--", color=AQUA, lw=1.4, label="Ledger run-rate (x12)")
    ax.plot(t.month, t.arr_billing_clean, color=BLUE, lw=2.8, label="Billing contracts, clean (reference)")
    mar = t[t.month == "2026-03-01"].iloc[0]
    ax.annotate("March 2026:\nraw export -€2.5M\nfor one day", (mar.month, mar.arr_billing_raw), xytext=(25, -45), textcoords="offset points",
                fontsize=8, color=ORANGE, arrowprops=dict(arrowstyle="->", color=ORANGE))
    ax.yaxis.set_major_formatter(meur)
    mfmt(ax)
    ax.set_title("ARR at month end, four sources")
    ax.legend(fontsize=8, loc="upper left")
    return save(fig, "arr_three")


def waterfall(month="2026-11-01", name="wf_nov"):
    w = m("fct_arr_waterfall")
    w = w[(w.month == month) & (w.step_order <= 6) & (w.step_order != 5)]
    labels = ["CRM as typed", "TCV on multi-year\ndeals (53)", "Amount before\nlast discount", "Closed-won with\nno contract (4)", "Billing contracts\n(reference)"]
    vals = w.amount_eur.tolist()
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    run = vals[0]
    ax.bar(0, vals[0], color=GREY)
    for i, v in enumerate(vals[1:4], 1):
        ax.bar(i, v, bottom=run, color=RED)
        ax.text(i, run + v / 2, f"{v / 1e6:+.2f}M", ha="center", va="center", fontsize=8, color="white" if abs(v) > 1e6 else INK)
        run += v
    ax.bar(4, vals[4], color=BLUE)
    for i, v in ((0, vals[0]), (4, vals[4])):
        ax.text(i, v, f"€{v / 1e6:.1f}M", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(range(5), labels, fontsize=8)
    ax.yaxis.set_major_formatter(meur)
    ax.set_ylim(0, vals[0] * 1.12)
    ax.set_title("CRM -> billing ARR, November 2026 (residual: €0)")
    return save(fig, name)


def march():
    t = m("fct_arr_three_values")
    t = t[(t.month >= "2026-01-01") & (t.month <= "2026-05-01")]
    n = m("fct_nrr_cohort")
    n = n[(n.cohort == "All") & (n.month >= "2026-01-01") & (n.month <= "2026-05-01")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.4, 3.0))
    x = np.arange(len(t))
    a1.bar(x - 0.2, t.arr_billing_raw / 1e6, 0.4, color=ORANGE, label="raw export")
    a1.bar(x + 0.2, t.arr_billing_clean / 1e6, 0.4, color=BLUE, label="contracts, clean")
    a1.set_xticks(x, t.month.dt.strftime("%b"))
    a1.set_ylim(18, 24.5)
    a1.set_title("ARR, €M")
    a1.legend(fontsize=7, loc="upper left")
    for basis, c, st in (("billing raw (by account)", ORANGE, "-"), ("contracts (clean)", BLUE, "-")):
        g = n[n.basis == basis]
        a2.plot(g.month.dt.strftime("%b"), g.nrr, st, marker="o", color=c, lw=2)
    a2.axhline(1, color=GREY, ls="--", lw=1)
    a2.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    a2.set_title("NRR 12 months")
    return save(fig, "march")


def bridge():
    b = m("fct_arr_monthly")
    b = b[b.basis == "contracts (clean)"]
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    w = 20
    ax.bar(b.month, b.new_arr, w, color=BLUE, label="New")
    ax.bar(b.month, b.expansion_arr, w, bottom=b.new_arr, color=AQUA, label="Expansion")
    ax.bar(b.month, b.contraction_arr, w, color=YELLOW, label="Contraction")
    ax.bar(b.month, b.churned_arr, w, bottom=b.contraction_arr, color=RED, label="Churn")
    ax.yaxis.set_major_formatter(keur)
    mfmt(ax)
    ax.set_title("ARR movements by month (contracts, clean)")
    ax.legend(fontsize=8, ncol=4, loc="upper left")
    return save(fig, "bridge")


def nrr():
    n = m("fct_nrr_cohort")
    a = n[n.cohort == "All"]
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    c = a[a.basis == "contracts (clean)"]
    r = a[a.basis != "contracts (clean)"]
    ax.plot(c.month, c.nrr, marker="o", color=BLUE, lw=2.6, label="NRR (reference)")
    ax.plot(c.month, c.grr, marker="o", color=AQUA, lw=2, label="GRR (reference)")
    ax.plot(r.month, r.nrr, ":", color=ORANGE, lw=2, label="NRR on raw billing export")
    ax.axhline(1, color=GREY, ls="--", lw=1)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    mfmt(ax)
    ax.set_title("Net and gross revenue retention, trailing 12 months")
    ax.legend(fontsize=8, loc="lower left")
    return save(fig, "nrr")


def cohort():
    n = m("fct_nrr_cohort")
    n = n[(n.basis == "contracts (clean)") & (n.month == n.month.max())]
    fig, ax = plt.subplots(figsize=(4.6, 3.3))
    ax.bar(n.cohort, n.nrr, color=[BLUE if c != "All" else INK for c in n.cohort], width=0.55, label="NRR")
    ax.scatter(n.cohort, n.grr, color=AQUA, zorder=3, s=40, label="GRR")
    for x, v, k in zip(n.cohort, n.nrr, n.customers_base):
        ax.text(x, v + 0.005, f"{v:.0%}\nn={k}", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0.85, 1.2)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    ax.set_title("By cohort (first contract year), Nov 2026")
    ax.legend(fontsize=8, loc="upper left")
    return save(fig, "cohort")


def ue_scatter():
    u = m("fct_unit_economics")
    u = u[u.month == u.month.max()]
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    neg = u.gross_margin_eur < 0
    ax.scatter(u.stored_tb[~neg], u.gross_margin_pct[~neg], s=8 + u.arr_eur[~neg] / 5000, color=BLUE, alpha=0.45, lw=0)
    ax.scatter(u.stored_tb[neg], u.gross_margin_pct[neg], s=8 + u.arr_eur[neg] / 5000, color=RED, alpha=0.9, lw=0)
    for r in u[neg].itertuples():
        ax.annotate(f"{r.customer_key} · flat fee · {r.retention_days} d", (r.stored_tb, r.gross_margin_pct), xytext=(-150, -2), textcoords="offset points", fontsize=7.5, color=RED)
    ax.set_xscale("log")
    ax.axhline(0, color=RED, ls="--", lw=1)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    ax.set_xlabel("TB of logs kept (log scale)")
    ax.set_title("Gross margin per customer vs data kept, Nov 2026")
    return save(fig, "ue_scatter")


def retention():
    u = m("fct_unit_economics")
    keys = u[(u.month == u.month.max()) & (u.gross_margin_eur < 0)].customer_key
    g = u[u.customer_key.isin(keys)].groupby("month").agg(rev=("revenue_month_eur", "sum"), ret=("storage_cost_eur", "sum"),
                                                         srch=("search_compute_cost_eur", "sum"), cogs=("cogs_eur", "sum")).reset_index()
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    ax.plot(g.month, g.rev, color=BLUE, lw=2.6, label="revenue (3 customers)")
    ax.plot(g.month, g.cogs, color=RED, lw=2, label="cost to serve")
    ax.fill_between(g.month, g.ret + g.srch, color=PINK, alpha=0.35, label="of which retention (storage + search)")
    ax.axvline(pd.Timestamp("2025-07-01"), color=GREY, ls="--", lw=1)
    ax.text(pd.Timestamp("2025-07-10"), g.rev.max() * 0.45, "retention\n120 -> 365 days", fontsize=8, color=MUTED)
    ax.yaxis.set_major_formatter(keur)
    mfmt(ax)
    ax.set_title("Three flat-fee customers: retention up, price unchanged")
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, 0.93))
    return save(fig, "retention")


def cloud_mix():
    c = pd.read_csv(ROOT / "data" / "sim" / "cloud_costs_focus.csv")
    fx = pd.read_csv(PUB / "ecb_usd_eur_monthly.csv").set_index("month").usd_per_eur
    c["m"] = c.ChargePeriodStart.str[:7]
    c["rate"] = c.m.map(fx).fillna(fx.iloc[-1])
    c["eur"] = np.where(c.BillingCurrency == "USD", c.BilledCost / c.rate, c.BilledCost)
    c["prod"] = c.Tags.map(lambda t: json.loads(t).get("product", "untagged") if t != "{}" else "untagged")
    p = c.pivot_table(index="m", columns="prod", values="eur", aggfunc="sum").fillna(0)
    p.index = pd.to_datetime(p.index)
    order = [("siem", BLUE, "SIEM (hosting)"), ("platform", GREY, "platform"), ("soar", AQUA, "SOAR"), ("cti", YELLOW, "CTI"), ("untagged", RED, "untagged (mostly AI)")]
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    bottom = np.zeros(len(p))
    for col, color, lab in order:
        if col in p:
            ax.bar(p.index, p[col], 20, bottom=bottom, color=color, label=lab)
            bottom += p[col].values
    rest = p.drop(columns=[o[0] for o in order if o[0] in p]).sum(axis=1)
    ax.bar(p.index, rest, 20, bottom=bottom, color=MUTED, label="staging")
    ax.yaxis.set_major_formatter(keur)
    mfmt(ax)
    ax.axvline(pd.Timestamp("2025-10-01"), color=GREY, ls="--", lw=1)
    ax.text(pd.Timestamp("2025-10-10"), bottom.max() * 0.97, "AI feature", fontsize=8, color=MUTED)
    ax.set_title("Cloud bill by product tag (EUR, service month)")
    ax.legend(fontsize=7.5, ncol=3, loc="upper left")
    return save(fig, "cloud_mix")


def gm_bench():
    g = m("fct_gross_margin")
    h = json.loads((MARTS / "headline.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(4.6, 3.3))
    ax.axhspan(h["bench_gm_min"], h["bench_gm_max"], color=GREY, alpha=0.25, lw=0)
    ax.text(g.month.iloc[1], h["bench_gm_min"] + 0.005, "listed vendors, latest 10-K", fontsize=8, color=MUTED)
    ax.plot(g.month, g.gross_margin_pct, color=BLUE, lw=2.6, marker="o", ms=3)
    ax.set_ylim(0.6, 0.9)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, 0))
    mfmt(ax)
    ax.set_title("Gross margin vs public benchmarks")
    return save(fig, "gm_bench")


def bva():
    b = m("fct_budget_vs_actual")
    g = b.groupby(["line_group", "budget_line"]).agg(bu=("budget_eur", "sum"), ac=("actual_eur", "sum")).reset_index()
    g["v"] = g.ac - g.bu
    g["fav"] = np.where(g.line_group == "Revenue", g.v >= 0, g.v <= 0)
    g = g.reindex(g.v.abs().sort_values().index).tail(10)
    fig, ax = plt.subplots(figsize=(8.2, 3.0))
    ax.barh(g.budget_line, g.v, color=np.where(g.fav, AQUA, RED))
    ax.xaxis.set_major_formatter(keur)
    ax.tick_params(axis="y", labelsize=8)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_title("Variance to budget, Jan-Nov 2026 (green = favorable)")
    return save(fig, "bva")


def travel():
    b = m("fct_budget_vs_actual")
    t = b[b.budget_line == "Travel and expenses"]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    x = np.arange(len(t))
    ax.bar(x - 0.2, t.budget_eur, 0.4, color=GREY, label="budget")
    ax.bar(x + 0.2, t.actual_eur, 0.4, color=BLUE, label="actual (approval month)")
    ax.set_xticks(x, t.month.dt.strftime("%b"), fontsize=8)
    ax.yaxis.set_major_formatter(keur)
    ax.annotate("kick-off end of Jan,\nclaimed in Feb", (1.2, t.actual_eur.iloc[1]), xytext=(25, -5), textcoords="offset points", fontsize=8, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED))
    ax.set_title("Travel and expenses, 2026")
    ax.legend(fontsize=8, loc="upper right")
    return save(fig, "travel")


def pvf():
    p = m("fct_cloud_price_volume_fx")
    r = p[p.comparison != "actual vs budget"].iloc[0]
    steps = [("Jun-Aug", r.base_eur, GREY), ("volume", r.volume_effect_eur, RED), ("price", r.price_effect_eur, AQUA), ("USD/EUR", r.fx_effect_eur, ORANGE), ("Sep-Nov", r.actual_eur, BLUE)]
    fig, ax = plt.subplots(figsize=(8.2, 3.0))
    run = r.base_eur
    for i, (lab, v, c) in enumerate(steps):
        if i in (0, 4):
            ax.bar(i, v, color=c)
            ax.text(i, v, f"€{v / 1e3:,.0f}k", ha="center", va="bottom", fontsize=8, fontweight="bold")
        else:
            ax.bar(i, v, bottom=run, color=c)
            ax.text(i, run + max(v, 0) + 1500, f"{v / 1e3:+,.1f}k", ha="center", va="bottom", fontsize=8)
            run += v
    ax.set_xticks(range(5), [s[0] for s in steps], fontsize=8)
    ax.set_ylim(r.base_eur * 0.92, r.actual_eur * 1.03)
    ax.yaxis.set_major_formatter(keur)
    ax.set_title(f"AWS bill, 3 months: FX = {r.fx_effect_eur / r.change_eur:.0%} of the rise")
    return save(fig, "pvf")


def headcount():
    h = m("fct_headcount_payroll")
    h = h[h.department == "All departments"]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.plot(h.month, h.hris_active_records, color=GREY, lw=1.6, label="HRIS active records")
    ax.plot(h.month, h.paid_persons, ":", color=ORANGE, lw=2, label="paid persons")
    ax.plot(h.month, h.headcount_reported, color=BLUE, lw=2.6, label="reported headcount")
    ax.plot(h.month, h.fte_reported, "--", color=AQUA, lw=1.4, label="FTE")
    mfmt(ax)
    ax.set_title("Headcount, three definitions")
    ax.legend(fontsize=7.5, loc="upper left")
    return save(fig, "headcount")


def build_all():
    return {f.__name__: f() for f in (bench_gm, bench_mix, arr_three, waterfall, march, bridge, nrr, cohort, ue_scatter, retention,
                                      cloud_mix, gm_bench, bva, travel, pvf, headcount)}


if __name__ == "__main__":
    print(build_all())
