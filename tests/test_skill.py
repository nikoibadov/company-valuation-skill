"""Offline tests: config validation, the any-ticker workbook (formulas == engine), weights, skill files."""
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

SKILL = Path(__file__).resolve().parents[1] / "skills" / "company-valuation"
sys.path.insert(0, str(SKILL / "scripts"))

import generic_export as gx  # noqa: E402
import valuate  # noqa: E402
from valuation import generic  # noqa: E402


def cfg_from(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text)
    return valuate.load_config(str(p))


def test_defaults_and_weights_replace(tmp_path):
    c = cfg_from(tmp_path, "company: ADBE\nweights: {DCF: 0.6, Comparable companies: 0.4}\n")
    assert not c["is_sap"] and c["edition"] == "web"
    assert c["weights"] == pytest.approx({"DCF": 0.6, "Comparable companies": 0.4})


def test_sap_alias_and_bad_inputs(tmp_path):
    assert cfg_from(tmp_path, "company: sap se\nedition: both\n")["is_sap"]
    with pytest.raises(SystemExit):
        cfg_from(tmp_path, "company: SAP\nassumptions: {erp: 5}\n")        # whole percent instead of decimal
    with pytest.raises(SystemExit):
        cfg_from(tmp_path, "company: SAP\nassumptions: {nonsense: 0.1}\n")
    with pytest.raises(SystemExit):
        cfg_from(tmp_path, "company: SAP\nedition: sideways\n")


def test_example_config_parses(tmp_path):
    p = tmp_path / "e.yaml"
    p.write_text(valuate.EXAMPLE)
    assert valuate.load_config(str(p))["company"] == "SAP"
    for f in (SKILL / "examples").glob("*.yaml"):
        valuate.load_config(str(f))


def synthetic():
    p = {"name": "Test Co", "ticker": "TST", "fin_ccy": "EUR", "q_ccy": "EUR", "fx": 1.0, "price": 50.0, "shares": 100.0,
         "rev0": 1000.0, "growth": [0.10, 0.09, 0.08, 0.07, 0.06], "margin0": 0.20, "margin_target": 0.25, "tax": 0.25,
         "da_pct": 0.04, "capex_pct": 0.05, "nwc_pct": 0.05, "g": 0.025, "rf": 0.03, "beta": 1.1, "erp": 0.05, "kd": 0.045,
         "tax_wacc": 0.25, "cash": 200.0, "debt": 300.0, "nci": 0.0, "mcap_fin": 5000.0, "sources": {"rf": "test"}}
    d = generic.dcf(p)
    peers = pd.DataFrame({"ticker": list("ABCDE"), "ev_sales_ntm": [3, 4, 5, 6, 7.0], "ev_ebit_ntm": [15, 18, 20, 22, 30.0],
                          "pe_ntm": [20, 22, 25, 28, 30.0], "rule40": [20, 25, 30, 35, 40.0]})
    s = {"info": {}, "rev_est": {}, "eps_est": {}}
    cp = generic.comps(p, s, peers)
    return {"inputs": p, "dcf": d, "scenarios": generic.scenarios(p), "comps": cp, "peers": peers, "grid_wacc_g": generic.grid_wacc_g(p),
            "market": {"price": 50.0, "price_date": "2026-11-13", "hi52": 60.0, "lo52": 40.0}, "dcf_band": (d["price"] * .9, d["price"] * 1.1)}


def test_workbook_formulas_reproduce_engine(tmp_path):
    res = synthetic()
    path, cell = gx.write_workbook(res, tmp_path / "t.xlsx", {"DCF": 0.6, "Comparable companies": 0.4})
    ok, msg = gx.verify_workbook(path, cell, res)
    assert ok, msg


def test_blended_renormalises_to_available_methods():
    res = synthetic()
    v, comp = gx.blended(res, {"DCF": 0.5, "Comparable companies": 0.25, "Precedent transactions": 0.25})
    want = (0.5 * comp["DCF"] + 0.25 * comp["Comparable companies"]) / 0.75
    assert v == pytest.approx(want)
    assert gx.blended(res, {"Precedent transactions": 1.0})[0] is None


def test_skill_files_are_consistent():
    text = (SKILL / "SKILL.md").read_text()
    assert text.startswith("---") and "name: company-valuation" in text and "description:" in text
    q = yaml.safe_load((SKILL / "questions.yaml").read_text())
    ids = [x["id"] for r in q["rounds"] for x in r["questions"]]
    assert {"company", "data_sources", "wacc", "weights", "peers", "price", "outputs"} <= set(ids)
    for r in q["rounds"]:
        assert len(r["questions"]) <= 4
        for x in r["questions"]:
            assert 2 <= len(x["options"]) <= 4, x["id"]
    wf = yaml.safe_load((SKILL / "workflow.yaml").read_text())
    assert {s["id"] for s in wf["steps"]} >= {"setup", "interview", "run", "sanity_review"}
    for f in ("reference/methodology.md", "reference/data_sources.md", "scripts/valuate.py", "scripts/setup_env.sh"):
        assert (SKILL / f).exists(), f
    assert not list(SKILL.rglob("bloomberg.yaml")), "licensed transcription must not ship"
