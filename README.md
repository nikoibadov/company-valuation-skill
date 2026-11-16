# company-valuation: a Claude Code skill that values a company for you

Say **"value SAP"** or **"run a DCF on Adobe as of 15 September"**. Claude first asks you a short set of questions (which company, which date, which data, which cost-of-capital view, how to weight the methods, which peers), then runs a reproducible valuation model and hands back a **checked Excel workbook, a football-field chart and a written summary**.

It was built for AIFA WiSe 26/27, Assignment 2 (Team 5, SAP SE). It values SAP with the full case-study model and any other listed non-financial company with a generic model.

## What it does

A valuation answers one question: what is a share worth, and does the market price agree? The skill answers it three ways and puts them on one chart:

| Method | What it does | Where it applies |
|---|---|---|
| **DCF** (FCFF) | Forecasts free cash flow for 10 years, discounts it at the WACC, adds a terminal value, bridges from enterprise value to equity value per share | SAP and any ticker |
| **Trading comparables** | Applies peer EV/sales, EV/EBIT and P/E multiples (25th, median, 75th percentile) to the company's numbers | SAP and any ticker |
| **Precedent transactions** | Applies EV/revenue multiples from 11 large software takeovers (2022 to 2026) | SAP only |

Around those sit scenarios (bear, base, bull), sensitivities, and for SAP a dividend discount model, a Monte Carlo simulation, a sum-of-the-parts and a bottom-up beta. The **football field** shows every method as a range against the share price, with a weighted value (default 50% DCF, 25% comps, 25% precedents).

## How it works

```
 you                Claude (SKILL.md)                       Python engine (scripts/)
  |  "value SAP"        |                                          |
  |-------------------->| 1. detect what is available  ----------> valuate.py sources
  |                     |    (data files, internet)                |
  |<--------------------| 2. interview (questions.yaml)            |
  |  answers            |    company, date, data, WACC,            |
  |-------------------->|    weights, peers, price, outputs        |
  |                     | 3. write valuation_config.yaml           |
  |                     | 4. run  -------------------------------> valuate.py run
  |                     |                                          |  load data as of the date
  |                     |                                          |  build assumptions (each with source)
  |                     |                                          |  DCF + comps + precedents
  |                     |                                          |  write Excel, charts, summary
  |                     |                                          |  recalculate Excel, must equal Python
  |<--------------------| 5. sanity review, then report            |
  |  value, caveats,    |    (flags +40% upside, TV share,         |
  |  files              |     thin peer sets, look-ahead)          |
```

Two things keep it honest:

- **Numbers come from code, not from the model's memory.** Claude writes a config and reads the outputs; it never types a valuation figure.
- **The Excel is checked.** After writing the workbook the skill recalculates every formula and fails if the result differs from the Python engine.

## The interview

Claude asks these before running anything (`skills/company-valuation/questions.yaml`). Every question has a recommended default.

| # | Question | Options |
|---|---|---|
| 1 | **Company** | SAP SE (full case-study model) / any listed company (you give the Yahoo ticker) |
| 2 | **Data sources** | Public web data (default) / Capital IQ + Bloomberg exports (SAP) / both side by side (SAP) |
| 3 | **Valuation date** | The case date 13 Nov 2026 (SAP) / today / a specific date you type |
| 4 | **WACC basis** | House view, ERP 5.0% / Damodaran implied ERP (live) / custom numbers |
| 5 | **Weighting** | 50/25/25 DCF/comps/precedents / DCF only / equal / custom |
| 6 | **Peers** | Default screen (SAP) or AI-proposed set you confirm (other tickers) / your own tickers / none |
| 7 | **Price** | Close on the valuation date / a price you type |
| 8 | **Outputs** | Excel workbook, charts, markdown summary, AI usage log |

After the first run Claude shows the key assumptions with their sources and asks whether to change any.

## The valuation date

The date you pick sets the **closing price**, the **10-year government yield**, the **beta regression window** and the **52-week range**. For SAP it also sets the **roll-forward** from the 30 Sep 2026 balance sheet and which **precedent deals** count (only those announced by then).

| | SAP | Other tickers |
|---|---|---|
| Allowed range | 30 Sep 2026 (balance sheet date) to today | Up to five years back to today |
| Default | 13 Nov 2026 (the case date) | Today |

**What an earlier date does not change:** peer multiples, consensus estimates, analyst targets and the financial statements are the latest available, so they contain information published after the date. The outputs carry a look-ahead warning. Read an earlier-date result as "today's model at that date's price and rates", not a point-in-time reconstruction (that needs Capital IQ history).

## What you get

In `valuation_output/`:

| File | Content |
|---|---|
| `SAP_Valuation_<edition>.xlsx` / `<TICKER>_Valuation.xlsx` | Formula-driven workbook with a live Bear/Base/Bull selector and an integrity-checks sheet. SAP: 19 sheets. Tickers: the same template (Assumptions with sources, WACC, Forecast, DCF, DDM, Checks, Scenarios, Sensitivity, Monte Carlo, Comps, Historicals, FCFF bridge); sheets with no data for the company are dropped |
| `football_*.png` | The football field, tornado and Monte Carlo charts (SAP also: revenue mix) |
| `summary_*.md` / `<TICKER>_summary.md` | Headline value vs price, method table, key numbers, where each input comes from, caveats |
| `valuation_config_used.yaml` | The exact inputs, so the run can be repeated |
| `AI_USAGE_LOG.md` | Skeleton of the log the assignment asks for; a human fills in the judgment calls |

## Install

**As a plugin** (inside Claude Code):

```
/plugin marketplace add nikoibadov/company-valuation-skill
/plugin install company-valuation@company-valuation-skill
```

**Or with the install script:**

```bash
git clone https://github.com/nikoibadov/company-valuation-skill.git
cd company-valuation-skill
./install.sh              # all your projects (~/.claude/skills)
./install.sh --project    # only the current project (./.claude/skills)
```

Needs Python 3.11+ and internet. The first run builds a virtual environment in `~/.company-valuation/venv` (about a minute).

## Use

In Claude Code: **"value SAP"**, **"run a DCF on Adobe"**, or `/company-valuation`.

Without Claude, the same engine runs from the command line:

```bash
PY=$(bash skills/company-valuation/scripts/setup_env.sh)
$PY skills/company-valuation/scripts/valuate.py sources                          # what is available, date ranges
$PY skills/company-valuation/scripts/valuate.py example > valuation_config.yaml  # edit it
$PY skills/company-valuation/scripts/valuate.py run --config valuation_config.yaml
```

Ready configs: `skills/company-valuation/examples/` (SAP web, SAP data edition, an Adobe run). A config is a few lines:

```yaml
company: SAP
edition: web
valuation_date: 2026-10-20
assumptions: {erp: damodaran}
weights: {DCF: 0.5, Comparable companies: 0.25, Precedent transactions: 0.25}
```

## Data edition (SAP only)

Capital IQ and Bloomberg files are licensed and are **not** in this repository. To use the data edition point the config at your own folder (`data_sources.capiq_dir`) and your transcription of the Bloomberg screens (`data_sources.bloomberg_yaml`); the skill guides Claude through making the transcription and asks a human to spot-check it. See `skills/company-valuation/reference/data_sources.md`.

## Repository layout

```
skills/company-valuation/
  SKILL.md          what Claude follows: interview, run, sanity review, report
  questions.yaml    the interview questions and options
  workflow.yaml     the workflow, deterministic vs AI-judgment steps
  reference/        methodology (incl. valuation date), data sources
  examples/         ready configs
  scripts/          valuate.py (entry point), the SAP and any-ticker engines, setup_env.sh
.claude-plugin/     plugin and marketplace manifests
tests/              offline tests: pytest tests
```

## Limits

- Banks, insurers, REITs and loss-making companies need other models; the skill says so and stops.
- Yahoo Finance data can be stale or wrong. Check price, shares, debt and consensus against filings before relying on a number.
- The any-ticker model holds the margin flat unless you set a target; a company in turnaround needs your view.
- The any-ticker model has no segment build and no precedent transactions (no public data); their weight goes to DCF and comps.
- Precedent transactions carry a control premium; treat them as a cross-check, not a price.
- Education only, not investment advice.

## Tests

```bash
~/.company-valuation/venv/bin/pip install pytest
~/.company-valuation/venv/bin/python -m pytest -q tests
```
