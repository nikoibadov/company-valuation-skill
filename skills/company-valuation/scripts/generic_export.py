"""Outputs for the any-listed-company mode: a formula-driven DCF workbook, a markdown summary and a football field.

The workbook's DCF sheet is live (change an input on the Inputs sheet and the value per share recalculates).
Peer multiples, sensitivities and scenarios are values from the Python engine. Recalculation is verified with the
`formulas` library, so the workbook and the engine cannot silently disagree."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

BLUE, BOLD = Font(color="0000FF"), Font(bold=True)
HEAD = PatternFill("solid", fgColor="1F3A5F")
WHITE = Font(bold=True, color="FFFFFF")
PCT_KEYS = ("m0", "mt", "tax", "da", "cx", "nwc", "g", "rf", "erp", "kd", "taxw")


def _head(ws, row, labels):
    for i, t in enumerate(labels, 1):
        c = ws.cell(row, i, t)
        c.fill, c.font = HEAD, WHITE


def write_workbook(res: dict, path: Path, weights: dict | None = None) -> tuple[Path, str]:
    p, sc, cp = res["inputs"], res["scenarios"], res["comps"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Inputs"
    ws["A1"] = f"{p['name']} ({p['ticker']}): valuation inputs"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = (f"Blue = input you can change. Reporting currency {p['fin_ccy']}, quote currency {p['q_ccy']}. "
                f"Amounts are in {p['fin_ccy']} units as reported (not millions).")
    rows = [("Share price (quote ccy)", p["price"], "price"), ("Shares outstanding", p["shares"], "shares"),
            ("Market cap (reporting ccy)", p["mcap_fin"], "mcap"), ("FX: quote units per reporting unit", p["fx"], "fx"),
            ("Revenue, last twelve months", p["rev0"], "rev0"), ("Operating margin today", p["margin0"], "m0"),
            ("Operating margin in year 5", p["margin_target"], "mt"), ("Tax rate on operating profit", p["tax"], "tax"),
            ("D&A % revenue", p["da_pct"], "da"), ("Capex % revenue", p["capex_pct"], "cx"),
            ("Net working capital % of revenue change", p["nwc_pct"], "nwc"),
            ("Terminal growth g", p["g"], "g"), ("Risk-free rate", p["rf"], "rf"), ("Beta (levered)", p["beta"], "beta"),
            ("Equity risk premium", p["erp"], "erp"), ("Pre-tax cost of debt", p["kd"], "kd"),
            ("Tax rate for the debt shield", p["tax_wacc"], "taxw"),
            ("Cash and investments", p["cash"], "cash"), ("Debt", p["debt"], "debt"), ("Non-controlling interests", p["nci"], "nci")]
    src = p.get("sources", {})
    notes = {"rf": src.get("rf"), "beta": src.get("beta"), "erp": src.get("erp"), "kd": src.get("kd"), "m0": src.get("margin"),
             "da": src.get("reinvestment"), "cx": src.get("reinvestment")}
    ref = {}
    _head(ws, 4, ["Input", "Value", "Source / rationale"])
    for i, (lab, v, key) in enumerate(rows, 5):
        ws.cell(i, 1, lab)
        c = ws.cell(i, 2, float(v))
        c.font = BLUE
        c.number_format = "0.00%" if key in PCT_KEYS else "#,##0.00"
        ws.cell(i, 3, notes.get(key) or "")
        ref[key] = f"Inputs!$B${i}"
    r0 = 5 + len(rows) + 1
    ws.cell(r0, 1, "Revenue growth years 1-5 (years 6-10 fade linearly to g)").font = BOLD
    ws.cell(r0 + 1, 1, "Growth rate")
    for k, gr in enumerate(p["growth"]):
        c = ws.cell(r0 + 1, 2 + k, float(gr))
        c.font, c.number_format = BLUE, "0.0%"
    ref["growth"] = [f"Inputs!${L(2 + k)}${r0 + 1}" for k in range(5)]
    ws.cell(r0 + 2, 1, src.get("growth") or "")
    ws.column_dimensions["A"].width, ws.column_dimensions["C"].width = 44, 70

    w = wb.create_sheet("WACC")
    w["A1"] = "WACC (CAPM)"
    w["A1"].font = Font(bold=True, size=13)
    w["A3"], w["B3"] = "Cost of equity", f"={ref['rf']}+{ref['beta']}*{ref['erp']}"
    w["A4"], w["B4"] = "Equity weight E/(E+D)", f"={ref['mcap']}/({ref['mcap']}+{ref['debt']})"
    w["A5"], w["B5"] = "Debt weight", "=1-B4"
    w["A6"], w["B6"] = "After-tax cost of debt", f"={ref['kd']}*(1-{ref['taxw']})"
    w["A7"], w["B7"] = "WACC", "=B4*B3+B5*B6"
    w["A7"].font = BOLD
    for r in (3, 4, 5, 6, 7):
        w.cell(r, 2).number_format = "0.00%"
    w.column_dimensions["A"].width = 30

    f = wb.create_sheet("DCF")
    f["A1"] = "FCFF DCF (mid-year discounting, 5 explicit + 5 fade years, Gordon terminal value)"
    f["A1"].font = Font(bold=True, size=13)
    _head(f, 3, ["Item"] + [f"Year {t}" for t in range(1, 11)])
    labels = ["Revenue growth", "Operating margin", "Revenue", "EBIT", "NOPAT", "D&A", "Capex", "Change in NWC", "FCFF",
              "Discount period", "Discount factor", "PV of FCFF"]
    for i, lab in enumerate(labels, 4):
        f.cell(i, 1, lab)
    G, M, REV, EBIT, NOP, DA, CX, DN, FC, PER, DF, PV = range(4, 16)
    for t in range(1, 11):
        c, col = L(1 + t), L(t)
        if t <= 5:
            f[f"{c}{G}"] = f"={ref['growth'][t - 1]}"
            f[f"{c}{M}"] = f"={ref['m0']}+({ref['mt']}-{ref['m0']})*{t}/5"
        else:
            f[f"{c}{G}"] = f"=$F${G}+({ref['g']}-$F${G})*{t - 5}/5"
            f[f"{c}{M}"] = f"={ref['mt']}"
        prev = ref["rev0"] if t == 1 else f"{col}{REV}"
        f[f"{c}{REV}"] = f"={prev}*(1+{c}{G})"
        f[f"{c}{EBIT}"] = f"={c}{REV}*{c}{M}"
        f[f"{c}{NOP}"] = f"={c}{EBIT}*(1-{ref['tax']})"
        f[f"{c}{DA}"] = f"={c}{REV}*{ref['da']}"
        f[f"{c}{CX}"] = f"={c}{REV}*{ref['cx']}"
        f[f"{c}{DN}"] = f"={ref['nwc']}*({c}{REV}-{prev})"
        f[f"{c}{FC}"] = f"={c}{NOP}+{c}{DA}-{c}{CX}-{c}{DN}"
        f[f"{c}{PER}"] = t - 0.5
        f[f"{c}{DF}"] = f"=1/(1+WACC!$B$7)^{c}{PER}"
        f[f"{c}{PV}"] = f"={c}{FC}*{c}{DF}"
        for r in (G, M):
            f[f"{c}{r}"].number_format = "0.0%"
        for r in (REV, EBIT, NOP, DA, CX, DN, FC, PV):
            f[f"{c}{r}"].number_format = "#,##0"
        f[f"{c}{DF}"].number_format = "0.000"
    k = 18
    items = [("Sum of PV of FCFF", f"=SUM(B{PV}:K{PV})"),
             ("Revenue year 11", f"=K{REV}*(1+{ref['g']})"),
             ("FCFF year 11", f"=B{k + 1}*{ref['mt']}*(1-{ref['tax']})+B{k + 1}*({ref['da']}-{ref['cx']})-{ref['nwc']}*(B{k + 1}-K{REV})"),
             ("Terminal value (Gordon)", f"=B{k + 2}/(WACC!$B$7-{ref['g']})"),
             ("PV of terminal value", f"=B{k + 3}/(1+WACC!$B$7)^10"),
             ("Enterprise value", f"=B{k}+B{k + 4}"),
             ("+ Cash", f"={ref['cash']}"), ("- Debt", f"=-{ref['debt']}"), ("- Non-controlling interests", f"=-{ref['nci']}"),
             ("Equity value", f"=SUM(B{k + 5}:B{k + 8})"),
             ("Value per share (quote ccy)", f"=B{k + 9}*{ref['fx']}/{ref['shares']}"),
             ("Current price", f"={ref['price']}"), ("Upside / downside", f"=B{k + 10}/B{k + 11}-1"),
             ("Terminal value share of EV", f"=B{k + 4}/B{k + 5}")]
    for i, (lab, fm) in enumerate(items, k):
        f.cell(i, 1, lab)
        f.cell(i, 2, fm).number_format = ("0.0%" if "Upside" in lab or "share of" in lab
                                         else "#,##0.00" if "per share" in lab or "price" in lab else "#,##0")
    f.cell(k + 10, 1).font = f.cell(k + 10, 2).font = BOLD
    f.column_dimensions["A"].width = 30
    price_cell = f"B{k + 10}"

    c = wb.create_sheet("Comps")
    c["A1"] = "Peer multiples and implied value per share (quote currency)"
    c["A1"].font = Font(bold=True, size=13)
    _head(c, 3, ["Method", "Peers (n)", "25th pct multiple", "Median multiple", "75th pct multiple", "Value @25th", "Value @median", "Value @75th"])
    for i, st in enumerate(cp["stats"].values(), 4):
        for j, v in enumerate([st["label"], st["n"], st["q1"], st["median"], st["q3"], st["p_q1"], st["p_med"], st["p_q3"]], 1):
            c.cell(i, j, v)
    if len(res["peers"]):
        r = 6 + len(cp["stats"])
        _head(c, r, list(res["peers"].columns))
        for i, row in enumerate(res["peers"].itertuples(index=False), r + 1):
            for j, v in enumerate(row, 1):
                c.cell(i, j, None if v != v else v)
    c.column_dimensions["A"].width = 34

    s = wb.create_sheet("Scenarios & sensitivity")
    _head(s, 1, ["Scenario", "Value per share", "Weight"])
    for i, (n_, v) in enumerate(((n_, v) for n_, v in sc.items() if n_ != "Weighted"), 2):
        s.cell(i, 1, n_)
        s.cell(i, 2, v["price"])
        s.cell(i, 3, v["weight"])
    s.cell(5, 1, "Probability-weighted")
    s.cell(5, 2, sc["Weighted"]["price"])
    g = res["grid_wacc_g"]
    s.cell(8, 1, "Value per share: WACC (rows) vs terminal growth (columns)").font = BOLD
    s.cell(9, 1, "WACC \\ g")
    for j, gg in enumerate(g.columns, 2):
        s.cell(9, j, float(gg)).number_format = "0.00%"
    for i, (wv, row) in enumerate(g.iterrows(), 10):
        s.cell(i, 1, float(wv)).number_format = "0.00%"
        for j, v in enumerate(row, 2):
            s.cell(i, j, None if v != v else float(v)).number_format = "0.0"
    s.column_dimensions["A"].width = 24

    n = wb.create_sheet("Notes")
    for i, t in enumerate([
            "Generated by the company-valuation skill (any-ticker mode).",
            "Data: Yahoo Finance (prices, statements, consensus), central-bank risk-free rate, Damodaran-style spreads. Public data only.",
            "The DCF sheet recalculates from the Inputs sheet. Comps, scenarios and sensitivities are values from the Python engine.",
            "Limits: one-segment model driven by TTM margins and consensus growth; banks and insurers need a different model.",
            f"Valuation date: {res.get('meta', {}).get('valuation_date', '')}. Price, risk-free rate, beta window and 52-week range are as of that date; "
            "peer multiples, consensus and analyst targets are the latest available" + (" (they include information published after the valuation date)." if res.get("meta", {}).get("lookahead") else "."),
            "Football-field weights: " + (", ".join(f"{k} {v:.0%}" for k, v in (weights or {}).items()) or "none")], 1):
        n.cell(i, 1, t).alignment = Alignment(wrap_text=True)
    n.column_dimensions["A"].width = 120
    wb._sheets = [wb["Inputs"], wb["WACC"], wb["DCF"], wb["Comps"], wb["Scenarios & sensitivity"], wb["Notes"]]
    wb.save(path)
    return path, price_cell


def verify_workbook(path: Path, price_cell: str, res: dict, tol: float = 0.01) -> tuple[bool, str]:
    import formulas
    sol = formulas.ExcelModel().loads(str(path)).finish().calculate()
    key = f"'[{path.name}]DCF'!{price_cell}".upper()
    got = next(float(v.value[0][0] if hasattr(v, "value") else v) for k, v in sol.items() if k.upper() == key)
    want = res["dcf"]["price"]
    ok = abs(got - want) <= tol
    return ok, f"Excel recalculation check: excel={got:,.4f} python={want:,.4f} -> {'OK' if ok else 'MISMATCH'}"


def blended(res: dict, weights: dict) -> tuple[float | None, dict]:
    """Weighted value per share over the methods that exist for this company (weights are renormalised)."""
    comp = {"DCF": res["dcf"]["price"]}
    meds = [st["p_med"] for st in res["comps"]["stats"].values()]
    if meds:
        comp["Comparable companies"] = sum(meds) / len(meds)
    w = {k: weights.get(k, 0) for k in comp}
    tot = sum(w.values())
    if tot <= 0:
        return None, comp
    return sum(w[k] * v for k, v in comp.items()) / tot, comp


def summary_md(res: dict, weights: dict, currency: str, valuation_date: str) -> str:
    from valuation import generic
    p, d, sc, mk = res["inputs"], res["dcf"], res["scenarios"], res["market"]
    wv, comp = blended(res, weights)
    out = [f"# {p['name']} ({p['ticker']}) valuation, {valuation_date}", "",
           f"**DCF value: {currency}{d['price']:.2f} per share** vs price {currency}{mk['price']:.2f} ({mk['price_date']}) "
           f"-> {d['upside']*100:+.1f}%. Scenarios: bear {currency}{sc['Bear']['price']:.0f} / base {currency}{sc['Base']['price']:.0f} / "
           f"bull {currency}{sc['Bull']['price']:.0f}; probability-weighted {currency}{sc['Weighted']['price']:.2f}.", ""]
    if wv is not None:
        out += [f"**Blended value {currency}{wv:.2f}** ("
                + ", ".join(f"{k} {currency}{v:.0f} x {weights.get(k, 0) / sum(weights.get(c, 0) for c in comp):.0%}" for k, v in comp.items())
                + "; weights renormalised over the methods available).", ""]
    out += ["| Method | Low | Mid | High |", "|---|---:|---:|---:|"]
    for it in generic.football_items(res):
        mid = f"{currency}{it['mid']:.0f}" if it["mid"] is not None else "-"
        out.append(f"| {it['label']} | {currency}{it['low']:.0f} | {mid} | {currency}{it['high']:.0f} |")
    peers = res["peers"]
    out += ["", "## Key numbers",
            f"- WACC {d['wacc']*100:.2f}%: Ke {d['ke']*100:.2f}% = {p['rf']*100:.2f}% + {p['beta']:.2f} x {p['erp']*100:.2f}%; "
            f"after-tax Kd {d['kd_at']*100:.2f}%; E/V {d['we']*100:.1f}%; g {p['g']*100:.2f}%",
            f"- Terminal value is {d['tv_share']*100:.0f}% of enterprise value",
            f"- Peers used: {len(peers)}" + (f" ({', '.join(peers['ticker'])})" if len(peers) else " (none: comps skipped)"),
            "", "## Where each input comes from"]
    out += [f"- **{k}**: {v}" for k, v in p.get("sources", {}).items()]
    if res.get("meta", {}).get("lookahead"):
        out += ["", f"**Look-ahead warning:** the valuation date ({valuation_date}) is earlier than today. Price, risk-free rate, beta window and the 52-week range are as of that date, "
                    "but peer multiples, consensus estimates, analyst targets and the financial statements are the latest available and include later information."]
    out += ["", "Limits: single-segment model on public data. Check every assumption before relying on the number."]
    return "\n".join(out)
