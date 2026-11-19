# Audit: does Kronos beat "the price stays the same"?

An independent re-check of one forward test of the open-source Kronos price-forecasting model.

Author: Ahmed Sadek (github.com/ahmed-sadek-dev). Date: 2026-11-18, revised 2026-11-19.

## Verdict

The result holds in direction. Its headline overstates the size of the sample.

- **Holds.** In this test the model's forecasts of closing prices were less accurate than assuming the price stays where it is. For the crypto targets that is true at every candle size, at both forecast distances, for all six crypto pairs, and on 3 of 4 days.
- **Clean data.** No forecast was saved after its candle started. Saved prices match the exchange in every sampled case.
- **Overstated.** "8,232 forward targets on 41 assets" is 2,010 forecasts saved during 45 clock hours on 6 days. 88.3% of the targets come from six crypto pairs and 86.0% from two days.
- **Not shown.** Nothing here says the model cannot forecast direction. Nothing covers other market conditions, other Kronos versions or fine-tuned models.

## What was tested

- **System:** Kronos-base (checkpoint `NeoQuasar/Kronos-base`), used as published, without fine-tuning.
- **Test:** the model sees past candles and forecasts the next candles. Each forecast is saved before the candles happen and scored afterwards.
- **Comparison:** "the price stays the same", meaning the last closing price the model saw.
- **Score:** skill = 1 - (model error / "stays the same" error). Above zero means the model is better. Errors are measured as a share of the last known price.
- **Data:** one table of 10,044 targets written by the test itself, reduced to the 14 columns this audit reads. 8,232 have an outcome. Prices are included for the 8,188 crypto targets. The 1,856 stock targets keep their timing and status only.

## Findings

1. **The forecasts are forward-only. Pass.** 0 of 8,232 scored targets were saved after their candle had started, and 0 outcomes were read before their candle had ended. 604 were saved less than 60 seconds before the start, which is close but not late.
2. **The comparison price is right. Pass.** Every crypto forecast uses one comparison price for all its targets. In a random sample of 120 crypto forecasts, it equals the exchange's closing price of the last candle the model saw in 120 of 120.
3. **The outcomes are right. Pass.** In the same sample, 495 of 495 saved outcomes equal the closing price in the exchange's own candle records.
4. **The model is less accurate than "stays the same". Confirmed.** Skill is -0.286 over the 7,266 scored crypto targets. By candle size it runs from -0.019 (1 to 5 minutes) to -1.491 (2 to 8 hours, only 150 targets). None of the six crypto pairs has a skill above zero. One day of four (2026-10-02, 110 targets) does.
5. **The result is not luck within this sample.** The targets overlap, so they are not 7,266 separate tests. Resampling whole clock hours (41 hours, 2,000 resamples) gives a 95% range of -0.428 to -0.174, and none of the resamples is above zero. Leaving out any one day keeps the skill between -0.336 and -0.178.
6. **The sample is much narrower than its headline.** 2,010 forecasts, 45 clock hours, 6 days. Two days hold 86.0% of the targets, six crypto pairs hold 88.3%, and 57.1% are on candles of 1 to 5 minutes.
7. **There is no single "skill" number.** Its size depends on how errors are pooled: -0.286 as a share of price, -0.254 in raw price units, -0.257 as the middle of the 60 symbol-and-candle-size groups. Pooled in raw price units, the two Bitcoin pairs carry 96.2% of the error with 34.2% of the targets. The sign is the same in every version.
8. **Direction is undecided.** The model had the direction right in 52.0% of the crypto targets that moved. Always guessing the more common direction is right in 52.2%. The difference ranges from -13.3 to +2.7 percentage points, so it could be zero.
9. **The next candle is barely tested.** Only 35 of the 8,232 scored targets are the next candle. The table holds 143 next-candle targets, so most of them have no outcome. None of the scored crypto targets is a next candle: 5,858 of the 7,266 are candles 2 to 5 ahead.
10. **Half of the stock targets were never scored.** 890 of 1,856 stock targets (48.0%) have no outcome, against 922 of 8,188 (11.3%) for crypto. The stock part of this test rests on about half of its targets.
11. **No rule was set beforehand.** The repository holds no pass or fail rule for accuracy written before the forecasts. The scores describe what happened. They do not test a prediction made in advance.

## What changed on 2026-11-19

I removed the stock prices from the public table, because I am not sure that I may republish them. The stock rows keep their timing and status, so the counts and the timing checks still cover all 10,044 targets.

Before the removal, the same script gave these figures on the full table: skill -0.100 over all 8,232 scored targets, -0.049 for the 966 stock targets, direction right in 52.4% against 50.7%, and a 95% range of -0.260 to -0.053. A figure of -0.165 quoted earlier for this test did not match the full table either. The figures in this section can no longer be regenerated from this repository. Every other figure in this report can.

## What a fair next test needs

- A rule written first, for example: skill above zero, with the whole 95% range above zero.
- One candle size and one forecast distance, chosen first.
- At least 30 separate days, with days as the unit of counting.
- An outcome for every target, or an explanation for each missing one.

## Limits of this audit

- It re-checks the table the test wrote. It did not re-run the model or re-check the model's input files.
- The exchange comparison covers crypto only. Stock prices were not re-checked.
- The checks were chosen after the headline result was known.
- One model version, six days inside three weeks of October 2026.

## Reproduce

```
python audit.py            # rewrites numbers.md from data/targets.csv and the saved exchange candles
python audit.py --fetch    # also downloads any missing candles from the public Binance market-data API
```

Python 3.10 or later, no packages. Every figure above is in `numbers.md`, except the full-table figures under "What changed".

Code and data: github.com/ahmed-sadek-dev/kronos-forward-test-audit

## How this was made

Method and code were produced with an AI coding agent under my direction. The figures in this report are written by `audit.py` from the stored table and can be regenerated with one command.

## License

MIT. See `LICENSE`.
