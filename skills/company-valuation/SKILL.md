---
name: company-valuation
description: Value a listed company as of a chosen date with an FCFF DCF, trading comparables and (for SAP) precedent transactions, and deliver a checked Excel workbook, football-field chart and summary. Interviews the user first about the company, valuation date, data sources, WACC basis, weighting, peers and outputs. Use when asked to value, price, run a DCF on, or build a football field for a company, or to re-run the SAP SE valuation case.
---

# Company valuation

You run a reproducible valuation. The numbers come from code (`scripts/valuate.py`); your job is to ask the right
questions, write the config, run it, check the result for sense, and report it honestly.

Two models sit behind one command:

| Mode | Used for | What you get |
|---|---|---|
| **SAP case study** (`company: SAP`) | AIFA Assignment 2; default valuation date 13 Nov 2026, any date from 30 Sep 2026 to today | Segment-driven DCF, comps, precedents, DDM, Monte Carlo, 19-sheet formula-driven Excel, football field |
| **Any ticker** (`company: NVDA`, `MC.PA`, `7203.T`) | Any listed non-financial company | One-segment DCF, peer comps, scenarios, formula-driven DCF workbook, football field |

Paths below are relative to this skill's folder (the folder holding this file).

## Rules that always apply

- **Never ask for, read, or type API keys, passwords or tokens.** No source here needs one.
- **Licensed data stays local.** Capital IQ exports and the Bloomberg transcription must never be committed, uploaded or pasted into an issue. Refer to them by path only.
- **No invented numbers.** Every figure you quote comes from the output files. If something is missing, say so.
- **Outcome first.** Lead the final report with the value and how it compares to the price, then the supporting numbers, then caveats.

## Workflow

### 1. Set up and detect what is available

```bash
PY=$(bash scripts/setup_env.sh)            # creates ~/.company-valuation/venv once; prints the Python path
$PY scripts/valuate.py sources             # JSON: Capital IQ / Bloomberg found? web endpoints reachable?
```

If the user already named a data folder, pass `--data-dir` and `--bloomberg-yaml`. Use the JSON to decide which
options are real: do not offer the data edition when `data_edition_possible` is false, unless the user can supply the
files (then see "Data edition without a transcription" below).

### 2. Interview the user

Read `questions.yaml` and ask with `AskUserQuestion`, **at most four questions per call**, in the order of the rounds
(Scope, then Details; the date question is in Scope). Skip a question whose `when` does not hold (for example the data-edition options when the company
is not SAP). Put the recommended option first. Then:

- If **Company** is "another listed company", ask for the Yahoo Finance ticker in plain text (exchange suffix for non-US
  names: `.DE`, `.PA`, `.L`, `.T`). Confirm the resolved company name and currency after the first run.
- **Valuation date.** The date sets the closing price, the 10-year government yield, the beta regression window, the
  roll-forward from the balance sheet (SAP: from 30 Sep 2026) and which precedent deals count (only those announced by
  that date). SAP accepts 30 Sep 2026 to today; other tickers up to five years back (`sources` prints the range).
  Take the date as `YYYY-MM-DD`; "today" and the SAP case date are options. **Say what an earlier date does not change:**
  peer multiples, consensus, analyst targets and the company's financial statements are the latest available, so they
  contain information published after that date (the outputs carry a look-ahead warning). For a true historical
  valuation the user needs a point-in-time data source such as Capital IQ.
- If **WACC basis** is "Custom numbers", ask for ERP and any of beta, risk-free rate, cost of debt, terminal growth.
  Convert percentages to decimals (5% becomes 0.05); `valuate.py` rejects values that look like whole percentages.
- If **Peers** is "AI-proposed" for a ticker, propose 6 to 10 listed peers with the same business model and a similar
  growth and margin profile, one line of reasoning each, and **wait for the user's confirmation**. This is a judgment step.
- If **Peers** is "I will give the tickers", take Yahoo tickers; for SAP the tickers are forced in (`include`) or
  dropped (`exclude`) from the built-in core set (see `scripts/valuation/loaders/common.py`, `PEER_CLASS`).

After the first run, show the key assumptions (terminal growth, margin path, beta, cost of debt, each with its source) and ask whether to change any before you report; re-run if so.

State plainly what an option does not do. For example, precedent transactions exist only for SAP, so for a ticker the
weights renormalise to DCF and comps.

### 3. Write the config and run

Write `valuation_config.yaml` in the user's working folder (`python scripts/valuate.py example` prints the schema and
`examples/` has three finished configs). Show it to the user in one block, then run:

```bash
$PY scripts/valuate.py run --config valuation_config.yaml --out valuation_output
```

The run fails, on purpose, if the Excel formulas do not reproduce the Python engine. If it fails, report the mismatch;
do not ship the workbook.

Outputs in `valuation_output/`: the workbook, football-field PNG, `*_summary.md`, `valuation_config_used.yaml` (the exact
inputs, so the run can be repeated) and an `AI_USAGE_LOG.md` skeleton. SAP also writes revenue-mix, tornado and Monte
Carlo charts, and `edition_compare.md` when both editions ran.

### 4. Sanity review (a judgment step, do not skip)

Read the summary and check before presenting. Flag anything that trips:

- Upside or downside beyond about 40%. Usually an input is off (margin, growth, peers) rather than the market being wrong. Say so and show what moves it (the sensitivity tables, the tornado). For a ticker, quote the reverse DCF from the summary: the margin, growth or WACC the share price implies, against the company's own history.
- Any line starting "Check:" in the summary (for example consensus revenue far from the last fiscal year): repeat it to the user.
- Terminal value above about 75% of enterprise value, or WACC within 2 points of terminal growth.
- Peer EV/EBIT quartiles very wide, or fewer than 5 peers in a multiple. Say the comps bar is weak.
- A bank, an insurer, a REIT, a loss-making company or one with a captive financing arm (car makers, machinery): `valuate.py` stops with "Model not applicable" and the reason. Pass the reason on; do not work around it.
- Valuation date earlier than today: the look-ahead warning must appear in the report, not only in the files.
- SAP: the data edition keeps the 5 Nov 2026 Bloomberg rates with the 13 Nov price; the web edition uses 13 Nov market data. Name the difference when both are shown.

### 5. Report

Give the user: the headline value per share against the price, the blended football-field value with its weights, what
drives the gap (WACC basis, terminal growth, peer multiples), the two or three assumptions to challenge, and the file
paths. For SAP also answer the assignment's intangibles question from the Intangibles sheet.

If the user wants a change, edit the config and re-run. Never edit numbers in the outputs by hand.

### 6. Log

Complete `AI_USAGE_LOG.md`: what you did, which steps were judgment calls (peer choice, ERP, deal selection), and any
errors found and fixed. A human signs off the judgment calls.

## Data edition without a transcription

The Bloomberg screens are images; `valuation/loaders/bloomberg.yaml` is a hand transcription of them. If the user has
the exports but no YAML: read each Bloomberg PNG, transcribe the values into a YAML following
`reference/data_sources.md` (cite the screenshot name for every block), and ask the user to spot-check at least the WACC,
beta, Bund curve and bond-yield screens before running. Point `data_sources.bloomberg_yaml` at the file.

## Reference

- `questions.yaml`: the interview (ids, options, which config key each answer sets)
- `workflow.yaml`: the same workflow, machine-readable, with deterministic vs AI-judgment steps
- `reference/methodology.md`: what each model does and where it stops
- `reference/data_sources.md`: every source, its licence status, and how the Bloomberg transcription works
- `scripts/valuate.py`: `sources`, `run`, `example`
- `examples/`: ready configs for SAP (web and data edition) and an any-ticker run
