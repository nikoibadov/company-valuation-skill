"""SAP SE valuation runner (called by valuate.py; can also be run directly).

    python run_valuation.py --edition data      # Capital IQ + Bloomberg exports (+ SAP IR gap fill)
    python run_valuation.py --edition web       # public web sources only
    python run_valuation.py --edition both      # both + edition comparison
    python run_valuation.py --edition data --price 215.40   # override the reference price (default: the 13 Nov 2026 close)

Outputs go to ./output: SAP_Valuation_<edition>.xlsx, football_<edition>.png, summary_<edition>.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from valuation import assumptions, charts, excel_writer, pipeline, verify  # noqa: E402

import os  # noqa: E402
OUT = Path(os.environ.get("VALUATION_OUT", ROOT / "output"))


def load(edition: str) -> dict:
    if edition == "data":
        from valuation.loaders import capiq
        return capiq.load()
    from valuation.loaders import web
    return web.load()


def run_edition(edition: str, price: float | None = None, check: bool = True, overrides: dict | None = None) -> dict:
    ds = load(edition)
    from valuation.loaders import public_refs
    public_refs.load(refresh_snapshot=True)        # keep the shipped snapshot of the reference data current
    if price:
        ds["market"]["price"] = price
        ds["market"]["price_source"] = "User override (run_valuation.py --price)"
    a = assumptions.build(ds)
    for k, v in (overrides or {}).items():          # user choices from the skill interview (valuate.py)
        a.set(k, v)
        a.items[k].source = "User choice (skill interview)"
    res = pipeline.run(ds, a)
    OUT.mkdir(parents=True, exist_ok=True)
    charts.football(res, OUT / f"football_{edition}.png",
                    f"SAP SE valuation football field, {edition.upper()} edition (€/share, 13 Nov 2026)")
    charts.revenue_mix(res, OUT / f"revenue_mix_{edition}.png")
    charts.tornado(res, OUT / f"tornado_{edition}.png")
    charts.monte_carlo(res, OUT / f"monte_carlo_{edition}.png")
    xlsx = excel_writer.write(res, OUT / f"SAP_Valuation_{edition}.xlsx", OUT)
    (OUT / f"summary_{edition}.md").write_text(summary_md(res))
    if check:
        ok, msg = verify.check_workbook(xlsx, res)
        print(msg)
        if not ok:
            raise SystemExit(f"Excel formulas do not reproduce the Python engine ({edition})")
    d = res["dcf"]
    print(f"[{edition}] DCF €{d['price']:.2f} | price €{res['market']['price']:.2f} | upside {d['upside']*100:+.1f}% | "
          f"WACC {d['wacc']*100:.2f}% | EV €{d['ev']/1000:.1f}bn -> {xlsx.name}")
    return res


def summary_md(res: dict) -> str:
    d, sc, cp, mk, a = res["dcf"], res["scenarios"], res["comps"], res["market"], res["assumptions"]
    st = cp["stats"]
    L = [f"# SAP SE valuation - {res['edition'].upper()} edition (valuation date 13 Nov 2026)", "",
         f"**DCF value: €{d['price']:.2f} per share** vs reference price €{mk['price']:.2f} ({mk['price_source']}, {mk['price_date']}) "
         f"→ {d['upside']*100:+.1f}%. Probability-weighted scenarios: €{sc['Weighted']['price']:.2f} "
         f"(bear €{sc['Bear']['price']:.0f} / base €{sc['Base']['price']:.0f} / bull €{sc['Bull']['price']:.0f}).", "",
         "| Method | Low | Mid | High |", "|---|---:|---:|---:|"]
    for it in charts.football_items(res):
        mid = f"€{it['mid']:.0f}" if it["mid"] is not None else "-"
        L.append(f"| {it['label']} | €{it['low']:.0f} | {mid} | €{it['high']:.0f} |")
    L += ["", "## Key numbers",
          f"- WACC {d['wacc']*100:.2f}% (Ke {d['ke']*100:.2f}% = {a['rf']*100:.2f}% + {a['beta']:.2f} x {a['erp']*100:.2f}%; Kd after tax {d['kd_at']*100:.2f}%; E/V {d['we']*100:.1f}%), g {a['g']*100:.2f}%",
          f"- EV €{d['ev']/1000:.1f}bn (TV {d['tv_share']*100:.0f}% of EV, implied exit EV/EBIT {d['exit_ev_ebit']:.1f}x), equity €{d['equity']/1000:.1f}bn, {a['shares']:.1f}m diluted shares",
          f"- Implied EV/NTM sales {d['implied_ev_sales_ntm']:.1f}x and EV/NTM EBIT {d['implied_ev_ebit_ntm']:.1f}x vs core-peer medians {st['ev_sales_ntm']['median']:.1f}x / {st['ev_ebit_ntm']['median']:.1f}x",
          f"- 2030E revenue €{d['forecast'].loc[2030,'revenue']/1000:.1f}bn (cloud {d['forecast'].loc[2030,'cloud_share']*100:.0f}%), FCFF 2027E €{d['forecast'].loc[2027,'fcff']/1000:.1f}bn",
          f"- Growth-adjusted regression: EV/NTM sales = {cp['regression']['intercept']:.2f} + {cp['regression']['slope']:.3f} x Rule-of-40 (R² {cp['regression']['r2']:.2f}, n={cp['regression']['n']})",
          *ext_md(res),
          "", "## FCFF 2027E-2030E (€m)", "", "| | 2026E | 2027E | 2028E | 2029E | 2030E |", "|---|---:|---:|---:|---:|---:|"]
    f = d["forecast"]
    for k, lab in (("revenue", "Revenue"), ("ebit", "EBIT"), ("nopat", "NOPAT"), ("da", "D&A"), ("capex", "Capex"), ("dnwc", "ΔNWC"), ("fcff", "FCFF")):
        L.append(f"| {lab} | " + " | ".join(f"{f.loc[y, k]:,.0f}" for y in range(2026, 2031)) + " |")
    L += ["", f"![football](football_{res['edition']}.png)", ""]
    return "\n".join(L)


def ext_md(res: dict) -> list[str]:
    x, a = res["ext"], res["assumptions"]
    s, b, t, w, br, pe = x["sotp"], x["beta"], x["tv"], x["wacc_iter"], x["bridge"], x["pe"]
    L = ["", "## Lecture-aligned cross-checks",
         f"- Sum of the parts: €{s['price']['median']:.0f} (€{s['price']['q1']:.0f}-€{s['price']['q3']:.0f}); cloud {s['cloud_share_of_rev']*100:.0f}% of NTM revenue, {s['cloud_share_of_ev']*100:.0f}% of SOTP EV. "
         f"Market price implies {s['implied_cloud']['market']:.1f}x sales for cloud vs peer median {s['parts'][0]['median']:.1f}x (SAP cloud grows {s['sap_cloud_growth']*100:.0f}% vs peers {s['peer_cloud_growth']*100:.0f}%)"]
    if b:
        L.append(f"- Bottom-up beta: unlevered {b['beta_u_median']:.2f} → re-levered {b['beta_relevered']:.2f} vs base {b['beta_base']:.2f}; WACC {b['wacc']*100:.2f}%, DCF €{b['price']:.0f}")
    L += [f"- Terminal value: zero growth €{t['zero']['price']:.0f} | Gordon €{t['gordon']['price']:.0f} | exit {t['exit']['mult_med']:.1f}x EBITDA €{t['exit']['price']:.0f}",
          f"- WACC weights iterated to the DCF equity value: {w['wacc']*100:.2f}% (start {w['wacc_start']*100:.2f}%), value €{w['price']:.2f}",
          f"- WACC tax shield at the German marginal rate {a['tax_wacc']*100:.0f}%",
          f"- Bridge: cheap-debt benefit €{br['debt_benefit']:.0f}m (+€{br['debt_benefit_ps']:.2f}), tax losses €{br['tlcf']:.0f}m (+€{br['tlcf_ps']:.2f}); NCI at market would be €{br['nci_ps_at_market']:.2f}",
          f"- P/E ex levered peers ({', '.join(q['ticker'] for q in pe['flagged']) or 'none'}): median {pe['median']:.1f}x vs {pe['median_all']:.1f}x → €{pe['p_med']:.0f}"]
    pr = res["prec"]
    L.append(f"- Precedent transactions ({pr['stats']['core']['n']} core deals of {pr['stats']['all']['n']}): median {pr['stats']['core']['median']:.1f}x EV/revenue "
             f"(SAP trades at {pr['sap_multiple']:.1f}x) → €{pr['prices']['core']['median']:.0f} (€{pr['prices']['core']['q1']:.0f}-€{pr['prices']['core']['q3']:.0f}). "
             f"Weighted 50/25/25 (DCF €{pr['components']['DCF']:.0f}, comps €{pr['components']['Comparable companies']:.0f}, precedents €{pr['components']['Precedent transactions']:.0f}): **€{pr['weighted']:.0f}**")
    dd, mc = x["ddm"], x["mc"]
    L += [f"- Dividend discount model: €{dd['price']:.0f} on dividends only (payout {dd['payout']*100:.0f}% rising to {dd['payout_terminal']*100:.0f}%); €{dd['total_payout_price']:.0f} if all free cash flow is paid out",
          f"- Monte Carlo ({mc['n']:,} runs): median €{mc['pct'][50]:.0f}, 5th-95th percentile €{mc['pct'][5]:.0f}-€{mc['pct'][95]:.0f}; {mc['p_above_price']*100:.0f}% of runs above the share price"]
    rf = x.get("refs")
    if rf:
        L.append("- External reference points: " + "; ".join(
            f"{inp} {('%.2f%%' % (v*100)) if v < 0.5 else ('%.2f' % v if v < 3 else '%.1fx' % v)} vs model {('%.2f%%' % (mv*100)) if mv < 0.5 else ('%.2f' % mv if mv < 3 else '%.1fx' % mv)}"
            for inp, _, v, mv, _ in rf["rows"]))
    return L


def compare(r_data: dict, r_web: dict) -> str:
    rows = []
    def add(lab, fa, fb, fmt="{:.2f}"):
        rows.append(f"| {lab} | {fmt.format(fa)} | {fmt.format(fb)} | {fmt.format(fb - fa) if isinstance(fa, (int, float)) else ''} |")
    da, dw = r_data["dcf"], r_web["dcf"]
    aa, aw = r_data["assumptions"], r_web["assumptions"]
    add("DCF value €/share", da["price"], dw["price"])
    add("Reference price €", r_data["market"]["price"], r_web["market"]["price"])
    add("WACC %", da["wacc"] * 100, dw["wacc"] * 100)
    add("Risk-free %", aa["rf"] * 100, aw["rf"] * 100)
    add("Beta", aa["beta"], aw["beta"])
    add("ERP %", aa["erp"] * 100, aw["erp"] * 100)
    add("Kd pre-tax %", aa["kd"] * 100, aw["kd"] * 100)
    add("EV €bn", da["ev"] / 1000, dw["ev"] / 1000)
    add("Comps EV/NTM sales median €", r_data["comps"]["stats"]["ev_sales_ntm"]["p_med"], r_web["comps"]["stats"]["ev_sales_ntm"]["p_med"])
    add("Comps P/NTM EPS median €", r_data["comps"]["stats"]["pe_ntm"]["p_med"], r_web["comps"]["stats"]["pe_ntm"]["p_med"])
    add("Analyst target mean €", r_data["market"]["tgt_mean"], r_web["market"]["tgt_mean"])
    txt = ["# Data edition vs Web edition", "",
           "Same engine, same operating assumptions (revenue build, margins, reinvestment, g). Differences come only from market inputs and data sources.", "",
           "| Item | Data (CIQ + Bloomberg) | Web (public) | Δ |", "|---|---:|---:|---:|", *rows, "",
           "Web-edition sources: SAP IR / SEC 6-K, yfinance (price, beta regression, peers, analyst estimates), Bundesbank (Bund yield), Damodaran (ERP cross-check)."]
    return "\n".join(txt)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", choices=["data", "web", "both"], default="both")
    ap.add_argument("--price", type=float, default=None, help="override reference share price (EUR); default is the 13 Nov 2026 close from Yahoo Finance")
    ap.add_argument("--no-check", action="store_true")
    args = ap.parse_args()
    eds = ["data", "web"] if args.edition == "both" else [args.edition]
    out = {e: run_edition(e, args.price, not args.no_check) for e in eds}
    if len(out) == 2:
        (OUT / "edition_compare.md").write_text(compare(out["data"], out["web"]))
        print("wrote output/edition_compare.md")
