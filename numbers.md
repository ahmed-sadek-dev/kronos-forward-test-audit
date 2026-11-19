# Numbers behind the audit (written by audit.py, seed 7)

Table: data/targets.csv, sha256 ae87c63fe1d3e00f
Prices: 7,266 of the 8,232 scored targets carry prices, all of them crypto. The stock rows keep their timing and status only, so sections 3 to 6 are about the crypto targets.

## 1. Sample
- Targets in the table: 10,044; scored: 8,232; never scored: 1,812
- Forecasts behind the scored targets: 2,010
- Symbols: 41; the 6 largest (BTCEUR, ETHUSDT, BTCUSDT, XRPEUR, SOLEUR, ETHEUR) hold 88.3% of the scored targets
- Calendar days: 6; the 2 largest hold 86.0%
- Distinct clock hours in which forecasts were saved: 45
- Share on 1 to 5 minute candles: 57.1%

## 2. Forward only
- Scored targets saved after their candle had started: 0
- Outcomes read before their candle had ended: 0
- Shortest gap between saving and candle start: 0 seconds; median 11 minutes
- Scored targets saved less than 60 seconds before their candle started: 604
- 'Next candle' targets: 35 scored of 143 in the table

## 3. Baseline
- Forecasts whose targets use more than one baseline price: 0

## 4. Saved prices against the exchange (random sample of crypto forecasts, Binance spot candles)
- Forecasts checked: 120 of 120 sampled (no exchange data: 0)
- Baseline equals the exchange close of the last candle the model saw: 120 of 120
- Outcome equals the exchange close of the target candle: 495 of 495

## 5. Headline recomputed
Skill = 1 - (sum of model errors / sum of 'stays the same' errors), errors as a share of the last known price.
- All scored targets with prices (crypto): skill -0.286, direction right 52.0% against 52.2% for the best constant guess (7,266 targets)
- 1 to 5 minute candles: skill -0.019, direction right 54.7% against 53.6% for the best constant guess (4,704 targets)
- 15 to 60 minute candles: skill -0.263, direction right 48.1% against 61.6% for the best constant guess (2,412 targets)
- 2 to 8 hour candles: skill -1.491, direction right 31.5% against 80.5% for the best constant guess (150 targets)
- candles 2 to 5 ahead: skill -0.278, direction right 52.1% against 51.2% for the best constant guess (5,858 targets)
- candles 6 to 13 ahead: skill -0.321, direction right 51.7% against 56.4% for the best constant guess (1,408 targets)
- Symbols with skill above zero: 0 of 6; among the 6 largest: 0 of 6
- Targets that did not move at all (left out of the direction count): 152
- Skill with errors pooled in raw price units instead: -0.254; there the BTC pairs carry 96.2% of the baseline error with 34.2% of the targets
- Middle skill over the 60 symbol-and-candle-size groups: -0.257

## 6. How sure
- 95% range of the skill when whole save-hours are resampled (41 hours, 2,000 resamples): -0.428 to -0.174
- Same for direction right minus best constant guess: -13.3 to +2.7 percentage points
- Share of resamples with skill above zero: 0.0%
- Skill per day: 2026-10-02 +0.113 (110); 2026-10-03 -0.243 (3,228); 2026-10-04 -0.429 (3,852); 2026-10-10 -0.496 (76)
- Skill with any one day left out: -0.336 to -0.178

## 7. Never scored
- crypto: 922 of 8,188 targets (11.3%)
- stock: 890 of 1,856 targets (48.0%)
