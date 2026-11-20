"""Finance reporting pack (excel/finance_reporting_pack.xlsx) with live formulas and a sheet that audits the workbook.

Inputs are the marts (data/marts/*.csv); every derived cell is an Excel formula (closing ARR, variances, price / volume / FX,
reconciliation status, gross margin, checks). Document properties are left empty.
    python src/build_excel.py            (add --verify to recalculate a copy with LibreOffice and read the Checks sheet)
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
OUT = ROOT / "excel" / "finance_reporting_pack.xlsx"

INK, MUTED, BLUE, RED = "0B0B0B", "52514E", "2A78D6", "B42F2F"
HEAD = PatternFill("solid", fgColor="EDEBE6")
SIM = PatternFill("solid", fgColor="FBE9E0")
INPUT = Font(color="1C5CAB")            # blue = value loaded from the warehouse; black = formula
EUR, PCT, NUM = '#,##0;[Red]-#,##0', '0.0%', '#,##0.000'


def m(name):
    return pd.read_csv(MARTS / f"{name}.csv")


def title(ws, text, sub):
    ws["A1"] = text
    ws["A1"].font = Font(size=14, bold=True, color=INK)
    ws["A2"] = sub
    ws["A2"].font = Font(size=10, color=MUTED)
    ws["A2"].fill = SIM


def header(ws, row, cols, widths=None):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row, j, c)
        cell.font = Font(bold=True, color=INK)
        cell.fill = HEAD
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[L(j)].width = w
    ws.freeze_panes = ws.cell(row + 1, 1)


def put(ws, r, c, v, fmt=None, inp=False):
    cell = ws.cell(r, c, None if (isinstance(v, float) and pd.isna(v)) else v)
    if fmt:
        cell.number_format = fmt
    if inp:
        cell.font = INPUT
    return cell


def about(wb, h):
    ws = wb.active
    ws.title = "About"
    title(ws, "Finance reporting pack - fictional cybersecurity SaaS scale-up", "SIMULATED data. Not Sekoia's numbers. Independent case study.")
    lines = [
        "Purpose: monthly Finance pack built from the warehouse marts (data/marts), with live formulas you can audit.",
        "Colour code: blue figures are loaded from the warehouse; black figures are Excel formulas.",
        "Sheets: ARR bridge | Budget vs actual (with AWS price / volume / FX) | Reconciliations | Unit economics | Checks.",
        "Reference definitions: docs/METRIC_DEFINITIONS.md. Reconciliation rules: docs/RECONCILIATIONS.md.",
        f"Latest month: November 2026. ARR (billing contracts, clean): EUR {h['arr_nov26']:,.0f}. NRR 12m: {h['nrr_clean_nov26']:.1%}.",
        "Rebuild: python src/run_sql.py, then python src/build_excel.py. Open the Checks sheet first: it must say ALL CHECKS PASS.",
    ]
    for i, t in enumerate(lines, 4):
        ws.cell(i, 1, t)
    ws.column_dimensions["A"].width = 120


def arr_bridge(wb):
    ws = wb.create_sheet("ARR bridge")
    title(ws, "ARR bridge by month (EUR) - reference: billing contracts, clean", "SIMULATED. Opening = previous closing; closing = opening + movements.")
    a = m("fct_arr_monthly")
    clean = a[a.basis == "contracts (clean)"].sort_values("month").reset_index(drop=True)
    raw = a[a.basis != "contracts (clean)"].sort_values("month").set_index("month")
    n = m("fct_nrr_cohort")
    nrr = n[(n.cohort == "All")].pivot_table(index="month", columns="basis", values="nrr")
    grr = n[(n.cohort == "All") & (n.basis == "contracts (clean)")].set_index("month").grr
    cols = ["Month", "Opening ARR", "New", "Expansion", "Contraction", "Churn", "Closing ARR", "Closing ARR (warehouse)", "Difference",
            "Customers", "NRR 12m", "GRR 12m", "", "ARR raw billing export", "Gap raw vs clean", "NRR 12m raw export", "NRR gap (pts)"]
    header(ws, 4, cols, [10, 14, 12, 12, 12, 12, 14, 16, 11, 10, 9, 9, 3, 16, 14, 12, 10])
    for i, r in clean.iterrows():
        row = 5 + i
        put(ws, row, 1, r.month[:7])
        if i == 0:
            put(ws, row, 2, r.arr_open, EUR, True)
        else:
            put(ws, row, 2, f"=G{row - 1}", EUR)
        for j, col in enumerate(["new_arr", "expansion_arr", "contraction_arr", "churned_arr"], 3):
            put(ws, row, j, r[col], EUR, True)
        put(ws, row, 7, f"=SUM(B{row}:F{row})", EUR)
        put(ws, row, 8, r.arr_close, EUR, True)
        put(ws, row, 9, f"=G{row}-H{row}", EUR)
        put(ws, row, 10, int(r.customers), "0", True)
        if r.month in nrr.index:
            put(ws, row, 11, nrr.loc[r.month, "contracts (clean)"], PCT, True)
            put(ws, row, 12, grr.loc[r.month], PCT, True)
            put(ws, row, 16, nrr.loc[r.month, "billing raw (by account)"], PCT, True)
            put(ws, row, 17, f"=(P{row}-K{row})*100", "0.0")
        put(ws, row, 14, raw.loc[r.month, "arr_close"], EUR, True)
        put(ws, row, 15, f"=N{row}-G{row}", EUR)
    last = 4 + len(clean)
    ws.cell(last + 2, 1, "March 2026: the raw export loses EUR 2.5M for one day (billing migration); clean ARR and the ledger do not move.").font = Font(italic=True, color=MUTED)
    return last


def budget(wb):
    ws = wb.create_sheet("Budget vs actual")
    title(ws, "Budget 2026 vs actual, January - November (EUR)", "SIMULATED. Budget frozen Dec 2025 (Pigment-like export); actual = ledger. Favorable: revenue above / cost below budget.")
    b = m("fct_budget_vs_actual")
    months = sorted(b.month.unique())
    lines = b[["line_group", "budget_line"]].drop_duplicates().sort_values(["line_group", "budget_line"]).values.tolist()
    nm = len(months)
    blocks = {"Budget": 5, "Actual": 5 + len(lines) + 3, "Variance (actual - budget)": 5 + 2 * (len(lines) + 3)}
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 38
    for c in range(3, 3 + nm + 4):
        ws.column_dimensions[L(c)].width = 12
    piv = {k: b.pivot_table(index="budget_line", columns="month", values=v) for k, v in (("Budget", "budget_eur"), ("Actual", "actual_eur"))}
    for name, top in blocks.items():
        ws.cell(top - 1, 1, name).font = Font(bold=True, color=BLUE)
        cols = ["Group", "Line"] + [x[:7] for x in months] + ["YTD"] + (["YTD %", "Favorable?"] if name.startswith("Variance") else [])
        for j, c in enumerate(cols, 1):
            cell = ws.cell(top, j, c)
            cell.font, cell.fill = Font(bold=True), HEAD
        for i, (grp, line) in enumerate(lines, 1):
            r = top + i
            put(ws, r, 1, grp)
            put(ws, r, 2, line)
            for k, mo in enumerate(months):
                c = 3 + k
                if name in piv:
                    put(ws, r, c, round(float(piv[name].loc[line, mo]), 2), EUR, True)
                else:
                    put(ws, r, c, f"={L(c)}{blocks['Actual'] + i}-{L(c)}{blocks['Budget'] + i}", EUR)
            put(ws, r, 3 + nm, f"=SUM(C{r}:{L(2 + nm)}{r})", EUR)
            if name.startswith("Variance"):
                ytd_b = f"{L(3 + nm)}{blocks['Budget'] + i}"
                put(ws, r, 4 + nm, f"=IF({ytd_b}=0,\"\",{L(3 + nm)}{r}/{ytd_b})", PCT)
                put(ws, r, 5 + nm, f"=IF(A{r}=\"Revenue\",IF({L(3 + nm)}{r}>=0,\"Favorable\",\"Unfavorable\"),IF({L(3 + nm)}{r}<=0,\"Favorable\",\"Unfavorable\"))")
        tot = top + len(lines) + 1
        put(ws, tot, 2, "Total costs (all lines except revenue)").font = Font(bold=True)
        for c in range(3, 4 + nm):
            put(ws, tot, c, f"=SUMIF($A${top + 1}:$A${top + len(lines)},\"<>Revenue\",{L(c)}{top + 1}:{L(c)}{top + len(lines)})", EUR)
    var_top, nlines = blocks["Variance (actual - budget)"], len(lines)

    # AWS price / volume / FX
    p = m("fct_cloud_price_volume_fx")
    p = p.assign(o=(p.comparison != "actual vs budget").astype(int)).sort_values(["o", "month"]).drop(columns="o")
    top = var_top + nlines + 5
    ws.cell(top - 1, 1, "AWS bill: price / volume / FX decomposition (EUR = list USD x (1 - discount) / USD per EUR)").font = Font(bold=True, color=BLUE)
    cols = ["Month", "Comparison", "Base list USD", "Base discount", "Base USD/EUR", "Actual list USD", "Actual discount", "Actual USD/EUR",
            "Base EUR", "Actual EUR", "Change", "Volume", "Price", "FX", "Check (= 0)"]
    for j, c in enumerate(cols, 1):
        cell = ws.cell(top, j, c)
        cell.font, cell.fill = Font(bold=True), HEAD
    for i, r in enumerate(p.itertuples(), 1):
        row = top + i
        put(ws, row, 1, r.month[:7])
        put(ws, row, 2, r.comparison)
        for j, (v, f) in enumerate([(r.base_list_usd, EUR), (r.base_discount, PCT), (r.base_usd_per_eur, NUM), (r.actual_list_usd, EUR),
                                    (r.actual_discount, PCT), (r.actual_usd_per_eur, NUM)], 3):
            put(ws, row, j, float(v), f, True)
        put(ws, row, 9, f"=C{row}*(1-D{row})/E{row}", EUR)
        put(ws, row, 10, f"=F{row}*(1-G{row})/H{row}", EUR)
        put(ws, row, 11, f"=J{row}-I{row}", EUR)
        put(ws, row, 12, f"=(F{row}-C{row})*(1-D{row})/E{row}", EUR)
        put(ws, row, 13, f"=F{row}*(D{row}-G{row})/E{row}", EUR)
        put(ws, row, 14, f"=F{row}*(1-G{row})*(1/H{row}-1/E{row})", EUR)
        put(ws, row, 15, f"=L{row}+M{row}+N{row}-K{row}", '0.00')
    return {"var_top": var_top, "nlines": nlines, "nm": nm, "pvf_top": top, "pvf_n": len(p), "act_top": blocks["Actual"], "bud_top": blocks["Budget"]}


def reconciliations(wb):
    ws = wb.create_sheet("Reconciliations")
    title(ws, "Reconciliations: every check, every month", "SIMULATED. Status recomputed by formula; the warehouse status is kept alongside to prove both agree.")
    r = m("fct_reconciliations").sort_values(["check_name", "month"])
    cols = ["Check", "Month", "Source A", "Source B", "Value A", "Value B", "Difference", "Explained", "Residual", "Threshold %",
            "Threshold (EUR or count)", "Status (formula)", "Status (warehouse)", "Same?", "Explanation"]
    header(ws, 4, cols, [36, 9, 34, 34, 14, 14, 12, 12, 11, 10, 12, 12, 12, 7, 60])
    for i, x in enumerate(r.itertuples(), 5):
        put(ws, i, 1, x.check_name)
        put(ws, i, 2, x.month[:7])
        put(ws, i, 3, x.source_a)
        put(ws, i, 4, x.source_b)
        put(ws, i, 5, float(x.value_a), EUR, True)
        put(ws, i, 6, float(x.value_b), EUR, True)
        put(ws, i, 7, f"=E{i}-F{i}", EUR)
        put(ws, i, 8, float(x.explained), EUR, True)
        put(ws, i, 9, f"=G{i}-H{i}", EUR)
        put(ws, i, 10, float(x.threshold_pct), '0.00%', True)
        put(ws, i, 11, f"=J{i}*ABS(F{i})", EUR)
        put(ws, i, 12, f"=IF(ABS(G{i})<0.5,\"OK\",IF(AND(A{i}=\"Bank vs ledger cash\",ABS(G{i})<=K{i}),\"WARN\",IF(ABS(G{i})<=K{i},\"OK\","
                       f"IF(ABS(I{i})<=MAX(K{i},0.5),\"EXPLAINED\",\"KO\"))))")
        put(ws, i, 13, x.status, None, True)
        put(ws, i, 14, f"=IF(L{i}=M{i},1,0)", "0")
        put(ws, i, 15, x.explanation if isinstance(x.explanation, str) else "")
    return 4 + len(r)


def unit_economics(wb):
    ws = wb.create_sheet("Unit economics")
    title(ws, "Unit economics per customer, November 2026 (EUR per month)", "SIMULATED usage x REAL public cloud unit prices. Revenue = ARR / 12. Sorted by gross margin.")
    u = m("fct_unit_economics")
    u = u[u.month == u.month.max()].sort_values("gross_margin_pct").reset_index(drop=True)
    cols = ["Customer", "Segment", "Plan", "Retention days", "Stored TB", "ARR", "Revenue / month", "Storage", "Search compute",
            "Ingest compute", "AI inference", "Shared platform", "Support & SOC ops", "Production tools", "COGS", "Gross margin",
            "Gross margin %", "Below zero?"]
    header(ws, 4, cols, [10, 12, 8, 9, 9, 12, 12, 10, 10, 10, 10, 10, 11, 10, 11, 12, 10, 9])
    for i, x in enumerate(u.itertuples(), 5):
        for j, v in enumerate([x.customer_key, x.segment, x.plan_type, x.retention_days, x.stored_tb], 1):
            put(ws, i, j, v, None, j > 3)
        put(ws, i, 6, float(x.arr_eur), EUR, True)
        put(ws, i, 7, f"=F{i}/12", EUR)
        for j, v in enumerate([x.storage_cost_eur, x.search_compute_cost_eur, x.ingest_compute_cost_eur, x.ai_cost_eur,
                               x.shared_platform_cost_eur, x.support_cost_eur, x.tools_cost_eur], 8):
            put(ws, i, j, round(float(v), 2), EUR, True)
        put(ws, i, 15, f"=SUM(H{i}:N{i})", EUR)
        put(ws, i, 16, f"=G{i}-O{i}", EUR)
        put(ws, i, 17, f"=IF(G{i}>0,P{i}/G{i},\"\")", PCT)
        put(ws, i, 18, f"=IF(P{i}<0,\"YES\",\"\")")
    last = 4 + len(u)
    ws["T4"], ws["U4"] = "Summary", ""
    ws["T4"].font = Font(bold=True)
    summary = [("Customers", f"=COUNTA(A5:A{last})", "0"), ("Customers below zero margin", f"=COUNTIF(R5:R{last},\"YES\")", "0"),
               ("Monthly loss on them", f"=-SUMIF(P5:P{last},\"<0\")", EUR), ("Revenue / month", f"=SUM(G5:G{last})", EUR),
               ("COGS / month", f"=SUM(O5:O{last})", EUR), ("Gross margin %", f"=1-U9/U8", PCT)]
    for k, (lab, f, fmt) in enumerate(summary, 5):
        put(ws, k, 20, lab)
        put(ws, k, 21, f, fmt)
    ws.column_dimensions["T"].width = 28
    ws.column_dimensions["U"].width = 14
    return last


def checks(wb, arr_last, bud, rec_last, ue_last, h):
    ws = wb.create_sheet("Checks")
    title(ws, "Checks: the workbook audits itself", "Each line recomputes a total two ways. Tolerance in EUR (or count). Overall status at the top.")
    pools = pd.read_csv(MARTS / "fct_unit_economics.csv")
    pools = float(pools[pools.month == pools.month.max()].cogs_eur.sum())
    vt, nl, nm, act, bt = bud["var_top"], bud["nlines"], bud["nm"], bud["act_top"], bud["bud_top"]
    ytd = L(3 + nm)
    pt, pn = bud["pvf_top"], bud["pvf_n"]
    rec_nov = h["arr_nov26"]
    rows = [
        ("ARR bridge: closing by formula = closing in the warehouse (sum of squared differences, 23 months)",
         f"=SUMSQ('ARR bridge'!I5:I{arr_last})", 0, 1),
        ("ARR bridge: November 2026 closing = sum of customer ARR in Unit economics",
         f"='ARR bridge'!G{arr_last}", f"=SUM('Unit economics'!F5:F{ue_last})", 1),
        ("ARR bridge: November 2026 closing = headline ARR (warehouse)", f"='ARR bridge'!G{arr_last}", rec_nov, 1),
        ("Budget vs actual: variance YTD (sum of lines) = actual YTD - budget YTD",
         f"=SUM('Budget vs actual'!{ytd}{vt + 1}:{ytd}{vt + nl})",
         f"=SUM('Budget vs actual'!{ytd}{act + 1}:{ytd}{act + nl})-SUM('Budget vs actual'!{ytd}{bt + 1}:{ytd}{bt + nl})", 1),
        ("Budget vs actual: cross-foot of the variance block (sum of months = sum of YTD)",
         f"=SUM('Budget vs actual'!C{vt + 1}:{L(2 + nm)}{vt + nl})", f"=SUM('Budget vs actual'!{ytd}{vt + 1}:{ytd}{vt + nl})", 1),
        ("AWS price + volume + FX = change, every row (sum of squared checks)", f"=SUMSQ('Budget vs actual'!O{pt + 1}:O{pt + pn})", 0, 1),
        ("AWS Sep-Nov vs Jun-Aug: FX share of the change", f"=INDEX('Budget vs actual'!N{pt + 1}:N{pt + pn},{pn})/INDEX('Budget vs actual'!K{pt + 1}:K{pt + pn},{pn})",
         round(h["aws_fx_share_sepnov"], 6), 0.001),
        ("Reconciliations: statuses by formula = statuses in the warehouse (rows that differ)",
         f"=COUNTA(Reconciliations!A5:A{rec_last})-SUM(Reconciliations!N5:N{rec_last})", 0, 0),
        ("Reconciliations: no KO status", f"=COUNTIF(Reconciliations!L5:L{rec_last},\"KO\")", 0, 0),
        ("Unit economics: allocated COGS = COGS pools of the warehouse (Nov 2026)", f"='Unit economics'!U9", pools, 1),
        ("Unit economics: customers below zero margin = 3 (retention event)", f"='Unit economics'!U6", h["underwater_customers_nov26"], 0),
    ]
    header(ws, 5, ["#", "Check", "Value (formula)", "Expected", "Difference", "Tolerance", "Result"], [4, 90, 16, 16, 12, 10, 10])
    for i, (lab, a, b, tol) in enumerate(rows, 6):
        put(ws, i, 1, i - 5)
        put(ws, i, 2, lab)
        put(ws, i, 3, a, '#,##0.000')
        put(ws, i, 4, b if isinstance(b, str) else float(b), '#,##0.000', not isinstance(b, str))
        put(ws, i, 5, f"=C{i}-D{i}", '#,##0.000')
        put(ws, i, 6, tol)
        put(ws, i, 7, f"=IF(ABS(E{i})<=F{i},\"PASS\",\"FAIL\")")
    last = 5 + len(rows)
    ws["B4"] = "Overall"
    ws["C4"] = f"=IF(COUNTIF(G6:G{last},\"FAIL\")=0,\"ALL CHECKS PASS\",\"CHECK FAILURES\")"
    ws["B4"].font = ws["C4"].font = Font(bold=True, size=12)
    return last


def build():
    h = json.loads((MARTS / "headline.json").read_text(encoding="utf-8"))
    wb = Workbook()
    about(wb, h)
    arr_last = arr_bridge(wb)
    bud = budget(wb)
    rec_last = reconciliations(wb)
    ue_last = unit_economics(wb)
    checks(wb, arr_last, bud, rec_last, ue_last, h)
    p = wb.properties
    p.creator = p.lastModifiedBy = p.title = p.subject = p.description = p.keywords = p.category = ""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print("written", OUT.relative_to(ROOT))


def verify():
    """Recalculate a copy with LibreOffice (headless) and read the Checks sheet: the Python stand-in for opening it in Excel."""
    soffice = shutil.which("soffice") or r"C:\Program Files\LibreOffice\program\soffice.exe"
    tmp = Path(tempfile.mkdtemp())
    subprocess.run([soffice, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(tmp), str(OUT)], check=True,
                   capture_output=True, timeout=180)
    ws = load_workbook(tmp / OUT.name, data_only=True)["Checks"]
    print("Overall:", ws["C4"].value)
    for r in ws.iter_rows(min_row=6, values_only=True):
        if r[0] is not None:
            print(f"  {r[6]}  {r[1][:80]}  value={r[2]!r:.14} expected={r[3]!r:.14}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    build()
    if "--verify" in sys.argv:
        verify()
