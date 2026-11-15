# Data sources

| Source | Used for | Needs | Licence / handling |
|---|---|---|---|
| Yahoo Finance (`yfinance`) | Prices, statements, consensus, peer multiples, beta regression | Internet | Public, personal-research use |
| SEC EDGAR XBRL | SAP statements cross-check (web edition) | Internet | Public |
| SAP investor relations (6-K statements) | SAP quarterly segment data, bonds, tax losses | Shipped in `valuation/loaders/sap_ir.yaml` | Public, hand-transcribed and cross-checked |
| Bundesbank | 10-year Bund yield | Internet | Public |
| ECB | AAA yield curve, inflation expectations, FX reference rates | Internet | Public |
| Damodaran (NYU Stern) | Implied ERP, default spreads, industry betas | Internet | Public |
| Precedent deals (`valuation/loaders/precedents.yaml`) | SAP precedent transactions | Shipped | Public sources, link per deal |
| S&P Capital IQ exports | SAP data edition: financials, consensus, peer list | Your licensed files | **Never commit or upload** |
| Bloomberg screenshots | SAP data edition: WACC inputs, beta, bond yields | Your licensed screens | **Never commit or upload** |

Fetches are cached per day under `<out_dir>/.cache` (SAP: `VALUATION_CACHE`). If today's download fails, the last good one is used and flagged.

## Bloomberg transcription (data edition)
Create a YAML with one block per screenshot, each with a `source:` naming the file. Blocks the model reads:
`price`, `wacc_screen` (wacc, equity_weight, cost_of_equity, debt_weight, cost_of_debt_after_tax, market_cap, st_debt, lt_debt),
`cost_of_equity_inputs` (risk_free, beta), `cost_of_debt_inputs` (pre_tax, tax_rate), `beta` (y2/y5 raw and adjusted), the Bund curve,
and the bond yields. Rates are in percent. A human must spot-check WACC, beta, the Bund curve and the bond yields against the screens.
Run `python scripts/valuate.py sources --bloomberg-yaml <file>` to confirm it is found.
