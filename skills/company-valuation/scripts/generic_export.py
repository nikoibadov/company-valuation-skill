"""Outputs for the any-listed-company mode: the SAP-template workbook, a markdown summary and a football field.

The workbook (valuation/generic_book.py) follows the SAP case model: Assumptions with sources and a live Bear/Base/Bull
selector, WACC, Forecast, DCF, DDM, Checks, Scenarios, Sensitivity, Monte Carlo, Comps, Historicals, FCFF bridge.
Recalculation is verified with the `formulas` library, so the workbook and the engine cannot silently disagree."""
from __future__ import annotations

from pathlib import Path


def write_workbook(res: dict, path: Path, weights: dict | None = None) -> tuple[Path, str]:
    """Full SAP-template workbook for any ticker (valuation/generic_book.py). Returns the path and the DCF price cell."""
    from valuation import generic_book
    path = generic_book.write(res, Path(path), Path(path).parent, weights)
    return path, "B36"


def verify_workbook(path: Path, price_cell: str, res: dict, tol: float = 0.01) -> tuple[bool, str]:
    """Recalculate the saved workbook and compare WACC, EV, equity, DCF and DDM values, the checks sheet and the
    Bear/Bull selector with the Python engine."""
    from valuation import generic_book
    return generic_book.verify(Path(path), res, scenarios=True, tol=tol)


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
    rv = res.get("reverse")
    if rv:
        f = lambda v, d=1: "no solution in range" if v is None else f"{v * 100:.{d}f}%"  # noqa: E731
        out += ["", "## What the share price implies (reverse DCF)",
                "One driver at a time, all else at the base case, until the DCF value equals the share price:",
                f"- Target EBIT margin {f(rv['margin_target']['implied'])} (base {f(rv['margin_target']['base'])})",
                f"- Revenue growth FY2-FY5 {f(rv['growth']['implied'])} a year (base {f(rv['growth']['base'])})",
                f"- WACC {f(rv['wacc']['implied'], 2)} (base {f(rv['wacc']['base'], 2)})",
                f"- Terminal growth {f(rv['g']['implied'], 2)} (base {f(rv['g']['base'], 2)})"]
    for wmsg in res.get("meta", {}).get("warnings", []):
        out += ["", f"**Check:** {wmsg}"]
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
