"""Headline figures read from the warehouse (nothing typed by hand). Used by the workbook, dashboard, PDF and README.
    python src/facts.py   -> data/marts/headline.json
"""
import json

from run_sql import OUT, connect


def one(con, sql):
    return con.execute(sql).fetchone()[0]


def build():
    con = connect()
    v = lambda sql: one(con, sql)
    h = {}
    t3 = lambda col, m: v(f"select {col} from fct_arr_three_values where month = date '{m}'")
    h["arr_nov26"] = t3("arr_billing_clean", "2026-11-01")
    h["arr_nov25"] = t3("arr_billing_clean", "2025-11-01")
    h["arr_dec24"] = t3("arr_billing_clean", "2024-12-01")
    h["arr_growth_yoy"] = h["arr_nov26"] / h["arr_nov25"] - 1
    h["customers_nov26"] = t3("customers_clean", "2026-11-01")
    h["crm_arr_nov26"] = t3("arr_crm_as_typed", "2026-11-01")
    h["crm_gap_pct"] = h["crm_arr_nov26"] / h["arr_nov26"] - 1
    w = lambda step, m="2026-11-01": v(f"select amount_eur from fct_arr_waterfall where month = date '{m}' and step_order = {step}")
    h["tcv_effect_nov26"], h["discount_effect_nov26"], h["orphan_effect_nov26"] = -w(2), -w(3), -w(4)
    h["orphan_deals_nov26"] = v("select orphan_deals from int_crm_arr_month where month = date '2026-11-01'")
    h["multi_year_deals_tcv"] = v("select count(*) from int_crm_deal_lines where contract_term_months > 12 and deal_type <> 'Upsell'")
    h["arr_raw_mar26"] = t3("arr_billing_raw", "2026-03-01")
    h["arr_clean_mar26"] = t3("arr_billing_clean", "2026-03-01")
    h["arr_gl_mar26"] = t3("arr_gl_runrate", "2026-03-01")
    h["migration_gap_lines"] = v("select count(*) from int_contracts_clean where gap_bridged")
    nrr = lambda m, basis, col="nrr": v(f"select {col} from fct_nrr_cohort where cohort = 'All' and basis = '{basis}' and month = date '{m}'")
    for m, k in (("2026-02-01", "feb26"), ("2026-03-01", "mar26"), ("2026-11-01", "nov26")):
        h[f"nrr_clean_{k}"] = nrr(m, "contracts (clean)")
        h[f"nrr_raw_{k}"] = nrr(m, "billing raw (by account)")
        h[f"grr_clean_{k}"] = nrr(m, "contracts (clean)", "grr")
    h["billing_accounts"] = v("select count(*) from int_customer_xref")
    h["customers_all_time"] = v("select count(distinct customer_key) from int_customer_xref")
    h["duplicate_accounts"] = h["billing_accounts"] - h["customers_all_time"]
    h["new_logos_raw_since_jun25"] = v("select sum(new_logos) from fct_arr_monthly where basis like 'billing raw%' and month >= date '2025-06-01' and month <> date '2026-04-01'")
    h["new_logos_clean_since_jun25"] = v("select sum(new_logos) from fct_arr_monthly where basis like 'contracts%' and month >= date '2025-06-01' and month <> date '2026-04-01'")
    hc = lambda col: v(f"select {col} from fct_headcount_payroll where department = 'All departments' and month = date '2026-11-01'")
    for col in ("hris_active_records", "headcount_reported", "fte_reported", "paid_persons", "interns", "apprentices", "suspected_leavers", "payroll_cost_eur"):
        h[f"hc_{col}"] = hc(col)
    g = lambda col, m="2026-11-01": v(f"select {col} from fct_gross_margin where month = date '{m}'")
    h["gross_margin_nov26"] = g("gross_margin_pct")
    h["gross_margin_avg_2026"] = v("select avg(gross_margin_pct) from fct_gross_margin where month >= date '2026-01-01'")
    h["cloud_pct_revenue_nov26"] = g("cloud_pct_revenue")
    h["cloud_total_nov26"] = g("cloud_total_eur")
    h["ai_cost_nov26"] = g("ai_inference_eur")
    h["ai_share_cloud_nov26"] = h["ai_cost_nov26"] / h["cloud_total_nov26"]
    h["untagged_cost_share_nov26"] = g("untagged_cloud_eur") / h["cloud_total_nov26"]
    h["untagged_resource_share_nov26"] = v("select avg(is_untagged::int) from int_cloud_costs_eur where month = date '2026-11-01'")
    h["untagged_resources_nov26"] = v("select sum(is_untagged::int) from int_cloud_costs_eur where month = date '2026-11-01'")
    h["resources_nov26"] = v("select count(*) from int_cloud_costs_eur where month = date '2026-11-01'")
    ue = "from fct_unit_economics where month = date '2026-11-01'"
    h["underwater_customers_nov26"] = v(f"select count(*) {ue} and gross_margin_eur < 0")
    h["underwater_loss_month_nov26"] = v(f"select -sum(gross_margin_eur) {ue} and gross_margin_eur < 0")
    h["underwater_margin_range"] = [v(f"select min(gross_margin_pct) {ue}"), v(f"select max(gross_margin_pct) {ue} and gross_margin_eur < 0")]
    under = [r[0] for r in con.execute(f"select customer_key {ue} and gross_margin_eur < 0").fetchall()]
    keys = ",".join(f"'{k}'" for k in under)
    st = lambda m: v(f"select sum(storage_cost_eur + search_compute_cost_eur) from fct_unit_economics where month = date '{m}' and customer_key in ({keys})")
    h["retention_storage_x"] = st("2025-07-01") / st("2025-06-01")
    h["retention_customers_gm_jun25"] = v(f"select sum(gross_margin_eur) / sum(revenue_month_eur) from fct_unit_economics where month = date '2025-06-01' and customer_key in ({keys})")
    h["retention_customers_gm_nov26"] = v(f"select sum(gross_margin_eur) / sum(revenue_month_eur) {ue} and customer_key in ({keys})")
    h["storage_cost_per_tb_nov26"] = v(f"select sum(storage_cost_eur + search_compute_cost_eur) / sum(stored_tb) {ue}")
    f = con.execute("select change_eur, volume_effect_eur, price_effect_eur, fx_effect_eur, base_usd_per_eur, actual_usd_per_eur from fct_cloud_price_volume_fx where comparison like 'Sep%'").fetchone()
    h["aws_change_sepnov"], h["aws_volume_sepnov"], h["aws_price_sepnov"], h["aws_fx_sepnov"], h["usd_rate_junaug"], h["usd_rate_sepnov"] = f
    h["aws_fx_share_sepnov"] = f[3] / f[0]
    b = con.execute("select sum(change_eur), sum(volume_effect_eur), sum(price_effect_eur), sum(fx_effect_eur) from fct_cloud_price_volume_fx where comparison = 'actual vs budget'").fetchone()
    h["aws_vs_budget_ytd"], h["aws_vs_budget_volume"], h["aws_vs_budget_price"], h["aws_vs_budget_fx"] = b
    tr = lambda m: con.execute(f"select budget_eur, actual_eur, variance_pct from fct_budget_vs_actual where budget_line = 'Travel and expenses' and month = date '{m}'").fetchone()
    h["travel_jan26"], h["travel_feb26"] = tr("2026-01-01"), tr("2026-02-01")
    h["sko_expenses"] = v("select sum(amount_eur) from stg_expenses where trip_tag = 'SKO-2026'")
    h["opex_variance_ytd"] = v("select sum(variance_eur) / sum(budget_eur) from fct_budget_vs_actual where line_group <> 'Revenue'")
    h["revenue_variance_ytd"] = v("select sum(variance_eur) / sum(budget_eur) from fct_budget_vs_actual where budget_line = 'SaaS subscriptions'")
    h["cash_nov26"] = v("select closing_cash from fct_cash where month = date '2026-11-01'")
    h["ocf_6m_avg_nov26"] = v("select operating_cf_6m_avg from fct_cash where month = date '2026-11-01'")
    h["bank_gl_diff_nov26"] = v("select bank_vs_gl_diff from fct_cash where month = date '2026-11-01'")
    h["bonus_accrual"] = v("select max(abs(diff)) from fct_reconciliations where check_name like 'Payroll%'")
    h["rev_cutoff"] = v("select max(abs(diff)) from fct_reconciliations where check_name like 'Billing vs ledger%'")
    h["cloud_cutoff"] = v("select max(abs(diff)) from fct_reconciliations where check_name like 'Cloud bills%'")
    rs = con.execute("select status, count(*) from fct_reconciliations group by 1 order by 1").fetchall()
    h["recon_status"] = {s: n for s, n in rs}
    bm = con.execute("select company, period_end, gross_margin, deferred_rev_pct_revenue, rnd_pct_revenue, sm_pct_revenue from fct_public_benchmarks qualify row_number() over (partition by company order by period_end desc) = 1 order by company").fetchall()
    h["benchmarks_latest"] = [{"company": r[0], "period_end": str(r[1]), "gross_margin": r[2], "deferred_rev_pct": r[3], "rnd_pct": r[4], "sm_pct": r[5]} for r in bm]
    h["bench_gm_min"], h["bench_gm_max"] = min(r[2] for r in bm), max(r[2] for r in bm)
    con.close()
    h = {k: (float(x) if hasattr(x, "__float__") and not isinstance(x, (int, bool)) else x) for k, x in h.items()}
    (OUT / "headline.json").write_text(json.dumps(h, indent=1, default=str), encoding="utf-8")
    return h


if __name__ == "__main__":
    h = build()
    print({k: (round(x, 3) if isinstance(x, float) else x) for k, x in h.items() if not isinstance(x, (list, dict))})
