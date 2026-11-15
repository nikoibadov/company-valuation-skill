# Methodology and limits

## Shared conventions
- **FCFF DCF**, mid-year discounting, 10 forecast years (5 explicit, 5 fading to terminal growth), Gordon-growth terminal value.
- **WACC** from CAPM: risk-free = 10-year government yield (Bundesbank for EUR), beta = 5-year weekly regression vs the local index, Blume-adjusted (0.67 raw + 0.33), ERP 5.0% by default, cost of debt = risk-free + a rating spread, tax shield at the marginal rate, market-value weights.
- **Equity bridge**: EV + cash - debt - non-controlling interests, divided by shares.
- **Comps**: NTM multiples (EV/sales, EV/EBIT, P/E) at the 25th, median and 75th percentile of the peer set, plus a growth-adjusted EV/sales regression on the Rule of 40.
- Share-based compensation is treated as a real cost (it is inside the operating margin).

## SAP case-study model
Segment-driven revenue (cloud, licences, support, services) with a 2026 anchor of 9M actuals plus a Q4 assumption; valuation anchored on the 30 Sep 2026 balance sheet and rolled forward 44 days to 13 Nov 2026 at the cost of equity. Extras: sum-of-the-parts, bottom-up beta, three terminal-value methods, WACC weight iteration, bridge refinements (cheap-debt benefit, tax-loss asset), dividend discount model, Monte Carlo (3,000 runs, seed 42), 11 precedent software deals with a 50/25/25 football-field weighting, bear/base/bull scenarios with a live selector in Excel.

## Any-ticker model
One segment: consensus growth for years 1-2 (Yahoo Finance), then a linear path; margin = trailing operating margin held flat unless overridden; D&A and capex = three-year average % of revenue; synthetic-rating spread from interest cover. Peers come from the user. The Excel DCF sheet is live; peer tables and sensitivities are values.

## Where it stops
- Banks, insurers, REITs, loss-making companies and pre-revenue companies need different models.
- Yahoo data can be wrong or stale; check price, shares, debt and revenue estimates against the company's filings before relying on the number.
- The any-ticker margin path is flat by default. A company mid-turnaround or with a structurally rising margin needs `margin_target` set by the user.
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
