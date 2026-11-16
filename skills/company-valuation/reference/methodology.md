# Methodology and limits

## Shared conventions
- **FCFF DCF**, mid-year discounting, 10 forecast years (5 explicit, 5 fading to terminal growth), Gordon-growth terminal value.
- **WACC** from CAPM: risk-free = 10-year government yield (Bundesbank for EUR), beta = 5-year weekly regression vs the local index, Blume-adjusted (0.67 raw + 0.33), ERP 5.0% by default, cost of debt = risk-free + a rating spread, tax shield at the marginal rate, market-value weights.
- **Tax**: effective rate in the explicit years, fading to the statutory (marginal) rate in the fade years; the statutory rate is also the debt tax shield (SAP: 29.93%, German corporate tax + solidarity surcharge 15.825% + trade tax 14.105%).
- **Equity bridge**: EV + cash and investments - debt incl. leases - pensions - non-controlling interests - preferred stock, divided by shares.
- **Comps**: NTM multiples (EV/sales, EV/EBIT, P/E) at the 25th, median and 75th percentile of the peer set, plus a growth-adjusted EV/sales regression on the Rule of 40.
- Share-based compensation is treated as a real cost (it is inside the operating margin).

## SAP case-study model
Segment-driven revenue (cloud, licences, support, services) with a 2026 anchor of 9M actuals plus a Q4 assumption; valuation anchored on the 30 Sep 2026 balance sheet and rolled forward 44 days to 13 Nov 2026 at the cost of equity. Extras: sum-of-the-parts, bottom-up beta, three terminal-value methods, WACC weight iteration, bridge refinements (cheap-debt benefit, tax-loss asset), dividend discount model, Monte Carlo (3,000 runs, seed 42), 11 precedent software deals with a 50/25/25 football-field weighting, bear/base/bull scenarios with a live selector in Excel.

## Any-ticker model (same template as SAP)
The workbook has the SAP layout: Cover, Summary, Assumptions (every input with source and rationale, live Bear/Base/Bull selector), WACC, Forecast, DCF, DDM, Checks, Scenarios, Sensitivity, Monte Carlo, Comps, Historicals, FCFF bridge, Sources & notes. Forecast, DCF, DDM, comps statistics and the weighted value are live formulas; grids, scenario values and Monte Carlo runs are engine values.

- **Base year** = last reported fiscal year; **anchor** = latest quarterly balance sheet on or before the valuation date; the current fiscal year is valued for the part still to come (stub), then the value is rolled forward to the valuation date at Ke (the SAP convention).
- **Revenue**: one segment; consensus for FY1-FY2 (Yahoo Finance), FY3-FY5 linear towards the midpoint of FY2 growth and g, FY6-FY10 fade to g.
- **Revenue beyond consensus**: growth above 25% is not extrapolated past FY2, and FY5 growth is at most 15%.
- **Margin**: FY1 = trailing-twelve-month operating margin (last four quarters), linear to a target by FY5. The target is the same margin unless it sits more than 5 points outside the range of the reported fiscal years (a cyclical peak or trough); then it is set halfway back to their average.
- **Tax**: 3-year average effective rate, fading to the statutory rate of the company's country.
- **D&A, capex**: 3-year averages in the explicit years. **Terminal capex** = D&A + g x net PP&E / revenue: in a steady state capex covers depreciation plus the growth of the asset base, so a build-out (or a pause) is not extrapolated for ever.
- **Working capital**: trade working capital (receivables + inventory - payables - deferred revenue) as % of revenue, applied to revenue growth.
- **Reverse DCF**: the target margin, growth, WACC or terminal growth at which the DCF equals the share price, each solved alone, shown against the company's history.
- **Guard**: banks, insurers, REITs, loss-makers, captive-finance companies and forecasts with negative long-run free cash flow are refused with the reason.
- **Bridge**: cash and short-term investments, long-term financial investments, total debt, minority interests and preferred stock from the quarterly balance sheet; pensions and other items are inputs (Yahoo does not report them).
- **Cross-checks**: dividend discount model (if the company pays a dividend), Monte Carlo (2,000 runs), tornado, four sensitivity grids, FCFF bridge from the model definition to reported free cash flow.
- **Dropped for tickers** (no public data): segment build, precedent transactions (weight redistributed to DCF and comps), intangibles, sum of the parts, bottom-up beta.

## Where it stops
- Banks, insurers, REITs, loss-making and pre-revenue companies, and companies with a financing arm need different models; the any-ticker model refuses them.
- Yahoo data can be wrong or stale; check price, shares, debt and revenue estimates against the company's filings before relying on the number.
- The any-ticker margin path is flat by default (normalised only at a cyclical extreme). A company mid-turnaround or with a structurally rising margin needs `margin_target` set by the user.
- The house ERP of 5.0% on top of a US risk-free rate above 5% gives US companies a WACC above 10%; most large US names then value below the market. Read the reverse DCF, and test the Damodaran ERP.
- Precedent transactions carry a control premium; read them as a cross-check, not a price.

## Valuation date
The date is an input (`valuation_date` in the config). What it moves and what it does not:

| Follows the date | Stays at the latest available |
|---|---|
| Closing price (last close on or before the date) | Peer multiples (EV/sales, EV/EBIT, P/E) |
| 10-year government yield (Bundesbank, or US Treasury) | Consensus revenue and EPS estimates |
| Beta regression window (5 years ending on the date) | Analyst price targets |
| 52-week range (history up to the date) | Financial statements (last reported period) |
| SAP: roll-forward days from the 30 Sep 2026 balance sheet; precedent deals announced after the date drop out | SAP Data edition: Bloomberg rates of 5 Nov 2026 |

Ranges: SAP 30 Sep 2026 (balance sheet date) to today; other tickers up to five years back to today. An earlier date therefore produces a value that uses some information published after it. Outputs say so (look-ahead warning). It is a "what would today's model say at that price and rate level" run, not a point-in-time reconstruction.
