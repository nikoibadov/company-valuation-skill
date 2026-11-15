# company-valuation: a Claude Code skill

A skill that values a listed company the way an analyst would: it **asks you what you want first** (company, data sources, WACC basis, weighting, peers, outputs), then runs a reproducible model and hands back a checked Excel workbook, a football-field chart and a summary.

Built for AIFA WiSe 26/27, Assignment 2 (Team 5, SAP SE). Works for SAP (full case-study model) and for any listed non-financial company.

## What you get

| | SAP SE case study | Any ticker |
|---|---|---|
| Model | Segment-driven FCFF DCF, comps, 11 precedent deals, DDM, Monte Carlo, SOTP, bottom-up beta | One-segment FCFF DCF, peer comps, scenarios |
| Excel | 19 sheets, formula-driven, Bear/Base/Bull selector | DCF sheet live, peers and sensitivities as values |
| Check | Workbook is recalculated and must equal the Python engine | Same |
| Data | Public web, or Capital IQ + Bloomberg exports | Public web |

## The interview

Claude asks these before running anything (`skills/company-valuation/questions.yaml`):

1. **Company**: SAP, or another ticker
2. **Data sources**: public web, Capital IQ + Bloomberg, or both side by side
3. **WACC basis**: house view (ERP 5.0%), Damodaran implied ERP, or custom numbers
4. **Weighting**: 50/25/25 DCF/comps/precedents, DCF only, equal, or custom
5. **Peers**: default screen, AI-proposed (you confirm), or your own tickers
6. **Price**: latest close or a price you give
7. **Assumption review**: after the run, or walk through the key ones first
8. **Outputs**: Excel, charts, summary, AI usage log

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
./install.sh              # for all your projects (~/.claude/skills)
./install.sh --project    # only the current project (./.claude/skills)
```

Needs Python 3.11+ and internet access. The first run creates a virtual environment in `~/.company-valuation/venv` (about a minute).

## Use

In Claude Code say **"value SAP"**, **"run a DCF on Adobe"**, or type `/company-valuation`. Answer the questions; the results land in `valuation_output/`.

Without Claude, the engine runs from the command line:

```bash
PY=$(bash skills/company-valuation/scripts/setup_env.sh)
$PY skills/company-valuation/scripts/valuate.py sources                       # what data is available
$PY skills/company-valuation/scripts/valuate.py example > valuation_config.yaml
$PY skills/company-valuation/scripts/valuate.py run --config valuation_config.yaml
```

Three ready configs are in `skills/company-valuation/examples/`.

## Data edition (SAP only)

The Capital IQ and Bloomberg files are licensed and are **not** in this repository. To use the data edition, point the config at your own folder (`data_sources.capiq_dir`) and your transcription of the Bloomberg screens (`data_sources.bloomberg_yaml`). The skill walks the agent through the transcription and asks a human to spot-check it. See `reference/data_sources.md`.

## Layout

```
skills/company-valuation/
  SKILL.md              the instructions Claude follows (interview, run, sanity review, report)
  questions.yaml        the interview questions and options
  workflow.yaml         the workflow, deterministic vs AI-judgment steps
  reference/            methodology, data sources
  examples/             ready configs
  scripts/              valuate.py (entry point), the engine, setup_env.sh
.claude-plugin/         plugin and marketplace manifests
tests/                  offline tests: pytest tests
```

## Limits

- Banks, insurers, REITs and loss-making companies need other models; the skill says so and stops.
- Yahoo Finance data can be stale or wrong. Check price, shares, debt and consensus before relying on a number.
- Education only, not investment advice.

## Tests

```bash
~/.company-valuation/venv/bin/pip install pytest
~/.company-valuation/venv/bin/python -m pytest -q tests
```
