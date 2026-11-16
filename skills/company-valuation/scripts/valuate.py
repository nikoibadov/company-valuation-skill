#!/usr/bin/env python3
"""Config-driven entry point of the company-valuation skill.

    valuate.py sources [--data-dir DIR]        what data is available here (JSON, used by the interview)
    valuate.py run --config valuation_config.yaml [--out DIR]
    valuate.py example                         print a commented example config

The agent fills the config from the user's answers (see questions.yaml). Everything the config can change is
validated here, so a typo fails loudly instead of silently running the default."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SAP_ALIASES = {"SAP", "SAP SE", "SAP.DE", "SAPGY"}
CASE_DATE = "2026-11-13"                      # SAP case valuation date (the engine is anchored on the 30 Sep 2026 balance sheet)
DEFAULTS = {
    "company": "SAP",
    "edition": "web",                         # SAP only: web | data | both
    "data_sources": {"capiq_dir": None, "bloomberg_yaml": None},
    "valuation_date": None,                   # YYYY-MM-DD or "today". null = SAP: 13 Nov 2026 case date; other tickers: today
    "price": None,
    "assumptions": {"erp": "house"},          # erp: house | damodaran | number; others: number
    "weights": {"DCF": 0.5, "Comparable companies": 0.25, "Precedent transactions": 0.25},
    "peers": {"tickers": [], "include": [], "exclude": []},
    "outputs": {"excel": True, "charts": True, "summary": True, "ai_log": True},
    "out_dir": "valuation_output",
}
SAP_KEYS = {"rf", "beta", "erp", "kd", "tax_wacc", "g", "sbc_addback"}
GENERIC_KEYS = {"rf": "rf", "beta": "beta", "erp": "erp", "kd": "kd", "tax_wacc": "tax_wacc", "g": "g",
                "tax": "tax", "tax_terminal": "tax_terminal", "margin_target": "margin_target", "margin0": "margin0",
                "nwc_pct": "nwc_pct", "da_pct": "da_pct", "capex_pct": "capex_pct", "capex_terminal": "capex_terminal",
                "sbc_addback": "sbc_addback", "pension": "pension", "other_nonop": "other_nonop"}


def _merge(base: dict, new: dict) -> dict:
    out = dict(base)
    for k, v in (new or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(path: str | None) -> dict:
    user = yaml.safe_load(Path(path).read_text()) if path else {}
    cfg = _merge(DEFAULTS, user or {})
    if (user or {}).get("weights"):
        cfg["weights"] = dict(user["weights"])        # the user's weights replace the defaults, they are not added to them
    cfg["company"] = str(cfg["company"]).strip()
    cfg["is_sap"] = cfg["company"].upper() in SAP_ALIASES
    errs = []
    if cfg["edition"] not in ("web", "data", "both"):
        errs.append("edition must be web, data or both")
    if cfg["is_sap"] is False and cfg["edition"] != "web":
        cfg["edition"] = "web"                # other companies: public data only
    w = {k: float(v) for k, v in cfg["weights"].items()}
    if any(v < 0 for v in w.values()) or sum(w.values()) <= 0:
        errs.append("weights must be non-negative and not all zero")
    else:
        cfg["weights"] = {k: v / sum(w.values()) for k, v in w.items()}
    allowed = SAP_KEYS if cfg["is_sap"] else set(GENERIC_KEYS)
    bad = set(cfg["assumptions"]) - allowed
    if bad:
        errs.append(f"unknown assumption(s) {sorted(bad)}; allowed: {sorted(allowed)}")
    for k, v in cfg["assumptions"].items():
        if k == "erp" and v in ("house", "damodaran"):
            continue
        try:
            cfg["assumptions"][k] = float(v)
        except (TypeError, ValueError):
            errs.append(f"assumption {k} must be a number")
    bounds = {"erp": (0, 0.15), "rf": (-0.01, 0.15), "kd": (0, 0.2), "g": (-0.02, 0.06), "tax_wacc": (0, 0.5), "tax": (0, 0.5),
              "tax_terminal": (0, 0.5), "margin_target": (-0.5, 0.9), "margin0": (-0.5, 0.9), "nwc_pct": (-0.5, 0.5),
              "da_pct": (0, 0.5), "capex_pct": (0, 0.5), "capex_terminal": (0, 0.5)}
    for k, (lo, hi) in bounds.items():
        v = cfg["assumptions"].get(k)
        if isinstance(v, float) and not lo <= v <= hi:
            errs.append(f"{k}={v} looks wrong: enter percentages as decimals (0.05 for 5%)")
    try:
        cfg["valuation_date"] = resolve_date(cfg["valuation_date"], cfg["is_sap"])
    except (ValueError, TypeError) as e:
        errs.append(str(e))
    if errs:
        raise SystemExit("Config problems:\n  - " + "\n  - ".join(errs))
    return cfg


def resolve_date(v, is_sap: bool) -> str:
    """Valuation date as ISO text, checked against what the model can support."""
    today = dt.date.today().isoformat()
    if isinstance(v, dt.date):
        v = v.isoformat()
    if v in (None, "", "default"):
        v = CASE_DATE if is_sap else today
    if str(v).lower() == "today":
        v = today
    from valuation import generic
    from valuation.loaders import common
    return common.check_sap_date(v) if is_sap else generic.check_date(v)


# ------------------------------------------------------------------ sources
def cmd_sources(a) -> None:
    out = {"python": sys.version.split()[0], "sap_case_date": CASE_DATE, "today": dt.date.today().isoformat(),
           "valuation_date_range": {"SAP": ["2026-09-30", dt.date.today().isoformat()],
                                   "other_tickers": [(dt.date.today() - dt.timedelta(days=5 * 365)).isoformat(), dt.date.today().isoformat()]}}
    if a.data_dir:
        os.environ["SAP_DATA_DIR"] = a.data_dir
    if a.bloomberg_yaml:
        os.environ["SAP_BLOOMBERG_YAML"] = a.bloomberg_yaml
    try:
        from valuation.loaders import capiq
        out["capital_iq_exports_found"] = bool(capiq.REPORT.exists())
        out["capital_iq_folder"] = str(capiq.CIQ)
        out["bloomberg_transcription_found"] = bool(capiq.BBG.exists())
        out["data_edition_possible"] = capiq.available()
    except Exception as e:  # noqa: BLE001
        out["data_edition_possible"] = False
        out["capital_iq_error"] = str(e)
    import requests
    net = {}
    for name, url in (("yahoo_finance", "https://query1.finance.yahoo.com/v7/finance/quote?symbols=SAP.DE"),
                      ("ecb", "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=1"),
                      ("bundesbank", "https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?lastNObservations=1"),
                      ("sec_edgar", "https://data.sec.gov/submissions/CIK0001000184.json")):
        try:
            net[name] = requests.get(url, timeout=8, headers={"User-Agent": "company-valuation-skill research"}).status_code < 500
        except Exception:  # noqa: BLE001
            net[name] = False
    out["web_sources_reachable"] = net
    out["web_edition_possible"] = net.get("yahoo_finance", False)
    print(json.dumps(out, indent=2))


# ------------------------------------------------------------------ SAP
def run_sap(cfg: dict, out: Path) -> dict:
    ds_ = cfg["data_sources"]
    if ds_.get("capiq_dir"):
        os.environ["SAP_DATA_DIR"] = str(Path(ds_["capiq_dir"]).expanduser())
    if ds_.get("bloomberg_yaml"):
        os.environ["SAP_BLOOMBERG_YAML"] = str(Path(ds_["bloomberg_yaml"]).expanduser())
    os.environ["VALUATION_OUT"] = str(out)
    os.environ.setdefault("VALUATION_CACHE", str(out / ".cache"))      # downloads are cached next to the outputs, never inside the skill
    import sap_runner
    from valuation import precedents
    from valuation.loaders import common

    sap_runner.OUT = out
    common.set_valuation_date(cfg["valuation_date"])
    if cfg["edition"] in ("data", "both"):
        from valuation.loaders import capiq
        if not capiq.available():
            raise SystemExit("Data edition needs the Capital IQ exports and a Bloomberg transcription. Missing: "
                             f"{capiq.REPORT if not capiq.REPORT.exists() else capiq.BBG}. Use edition: web, or point "
                             "data_sources.capiq_dir / bloomberg_yaml at your files.")
    # football-field weights
    precedents.WEIGHTS.clear()
    precedents.WEIGHTS.update(cfg["weights"])
    for k in ("DCF", "Comparable companies", "Precedent transactions"):
        precedents.WEIGHTS.setdefault(k, 0.0)
    # peer screen
    for t in cfg["peers"]["exclude"]:
        if t in common.PEER_CLASS:
            common.PEER_CLASS[t] = (common.PEER_CLASS[t][0] + " (excluded by user)", False)
    for t in cfg["peers"]["include"]:
        if t in common.PEER_CLASS:
            common.PEER_CLASS[t] = (common.PEER_CLASS[t][0] + " (included by user)", True)
    ov = {k: v for k, v in cfg["assumptions"].items() if k != "erp" or isinstance(v, float)}
    if cfg["assumptions"].get("erp") == "damodaran":
        from valuation.loaders import web
        d = web.damodaran()
        ov["erp"] = d["erp"] + d["us_default_spread"]
    editions = ["data", "web"] if cfg["edition"] == "both" else [cfg["edition"]]
    res = {e: sap_runner.run_edition(e, price=cfg["price"], overrides=ov) for e in editions}
    if len(editions) == 2:
        (out / "edition_compare.md").write_text(sap_runner.compare(res["data"], res["web"]))
    return res


# ------------------------------------------------------------------ any ticker
def run_generic(cfg: dict, out: Path) -> dict:
    os.environ.setdefault("VALUATION_CACHE", str(out / ".cache"))
    from valuation import charts, generic
    import generic_export as gx

    ov = {}
    a = cfg["assumptions"]
    for k, v in a.items():
        if k == "erp" and v == "house":
            continue
        if k == "erp" and v == "damodaran":
            from valuation.loaders import web
            d = web.damodaran()
            v = d["erp"] + d["us_default_spread"]
        ov[GENERIC_KEYS[k]] = v
    if cfg["price"]:
        ov["price"] = float(cfg["price"])
    peers = list(cfg["peers"]["tickers"])
    try:
        res = generic.run(cfg["company"], overrides=ov, peer_tickers=peers, vdate=cfg["valuation_date"])
    except generic.ModelNotApplicable as e:
        raise SystemExit(f"Model not applicable. {e}")
    p = res["inputs"]
    cur = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF "}.get(p["q_ccy"], p["q_ccy"] + " ")
    today = cfg["valuation_date"]
    tag = p["ticker"].replace(".", "_")
    if cfg["outputs"]["excel"]:
        x, cell = gx.write_workbook(res, out / f"{tag}_Valuation.xlsx", cfg["weights"])
        ok, msg = gx.verify_workbook(x, cell, res)
        print(msg)
        if not ok:
            raise SystemExit("Excel formulas do not reproduce the Python engine")
    if cfg["outputs"]["charts"]:
        items = generic.football_items(res)
        wv, _ = gx.blended(res, cfg["weights"])
        charts.football(res, out / f"{tag}_football.png", f"{p['name']}: football field ({p['q_ccy']} per share, {today})", items=items, currency=cur)
    if cfg["outputs"]["summary"]:
        (out / f"{tag}_summary.md").write_text(gx.summary_md(res, cfg["weights"], cur, today))
    d = res["dcf"]
    print(f"[{p['ticker']}] DCF {cur}{d['price']:.2f} | price {cur}{p['price']:.2f} | upside {d['upside']*100:+.1f}% | WACC {d['wacc']*100:.2f}%")
    return res


EXAMPLE = """\
# valuation_config.yaml: written by the agent from the interview answers
company: SAP                  # SAP = the full case-study model; or any Yahoo ticker, e.g. NVDA, MC.PA, 7203.T
edition: web                  # SAP only: web (public data) | data (Capital IQ + Bloomberg exports) | both
data_sources:                 # data edition only
  capiq_dir: null             # folder that contains 'S&P Capital IQ/SAP/*.xlsx'
  bloomberg_yaml: null        # your transcription of the Bloomberg screenshots
valuation_date: null          # YYYY-MM-DD or "today". null = SAP 13 Nov 2026 (case date) / today for other tickers
                              # SAP range 2026-09-30..today; other tickers up to 5 years back. Drives price, rates, beta window, roll-forward
price: null                   # null = close on the valuation date; or a number to override
assumptions:
  erp: house                  # house (5.0%) | damodaran (live implied ERP) | a number such as 0.0429
  # beta: 0.98              # optional overrides, decimals: rf, beta, kd, g, tax_wacc (any company); tax, tax_terminal,
                              # margin_target, nwc_pct, capex_pct (tickers); pension, other_nonop in reporting-currency units
weights:                      # football-field blend, renormalised over the methods that exist
  DCF: 0.50
  Comparable companies: 0.25
  Precedent transactions: 0.25   # SAP only
peers:
  tickers: []                 # any ticker: the peer set (Yahoo symbols)
  include: []                 # SAP: force these loaded peers into the core set
  exclude: []                 # SAP: drop these from the core set
outputs: {excel: true, charts: true, summary: true, ai_log: true}
out_dir: valuation_output
"""


def cmd_run(a) -> None:
    cfg = load_config(a.config)
    out = Path(a.out or cfg["out_dir"]).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "valuation_config_used.yaml").write_text(yaml.safe_dump({k: v for k, v in cfg.items() if k != "is_sap"}, sort_keys=False))
    print(f"Valuing {cfg['company']} ({'SAP case-study model' if cfg['is_sap'] else 'any-ticker model'}) -> {out}")
    res = run_sap(cfg, out) if cfg["is_sap"] else run_generic(cfg, out)
    if cfg["outputs"]["ai_log"]:
        (out / "AI_USAGE_LOG.md").write_text(ai_log(cfg))
    print("Done. Files:", ", ".join(sorted(p.name for p in out.iterdir() if p.is_file())))
    return res


def ai_log(cfg: dict) -> str:
    return "\n".join([
        "# AI usage log (fill in the judgment calls)", "",
        f"- Date: {dt.date.today().isoformat()}", f"- Company: {cfg['company']}, edition: {cfg['edition']}",
        f"- Valuation date: {cfg['valuation_date']}", f"- Config used: valuation_config_used.yaml", "",
        "## What the AI did", "- Asked the interview questions, wrote the config, ran `valuate.py`, read the outputs.", "",
        "## Judgment calls a human must sign off", "- Peer set, ERP, beta, terminal growth, margin path, deal selection (SAP precedents).", "",
        "## Issues found and fixed", "- (add here)"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sources")
    s.add_argument("--data-dir")
    s.add_argument("--bloomberg-yaml")
    r = sub.add_parser("run")
    r.add_argument("--config")
    r.add_argument("--out")
    sub.add_parser("example")
    a = ap.parse_args()
    if a.cmd == "example":
        print(EXAMPLE)
    elif a.cmd == "sources":
        cmd_sources(a)
    else:
        cmd_run(a)


if __name__ == "__main__":
    main()
