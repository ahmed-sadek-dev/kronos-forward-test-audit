"""Independent audit of a forward test of the Kronos price-forecasting model.

Reads one table of saved forecasts and their outcomes (data/targets.csv), re-checks it and writes numbers.md.
The question: is "Kronos-base forecasts the next closes worse than 'the price stays the same'" a sound result?
The public table holds prices for the crypto targets only. The stock rows keep their timing and status, so counts
and timing checks cover every target while every accuracy figure is about the crypto targets.

Usage: python audit.py           (uses the saved exchange candles in data/exchange_candles.json)
       python audit.py --fetch   (downloads missing candles from the public Binance market-data API first)
"""
import csv
import hashlib
import json
import random
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
TABLE = HERE / "data" / "targets.csv"
CANDLES = HERE / "data" / "exchange_candles.json"
SEED, RESAMPLES, SAMPLE_FORECASTS = 7, 2000, 120
T = datetime.fromisoformat


def minutes(frame):
    return int(frame[:-1]) * {"m": 1, "h": 60, "d": 1440}[frame[-1]]


def load():
    rows = list(csv.DictReader(open(TABLE, encoding="utf-8", newline="")))
    for r in rows:
        r["h"] = int(r["horizon"])
        if r["status"] != "Matched" or not r["baseline_close"]:  # stock rows carry no prices in the public table
            continue
        p, a, b = (float(r[k]) for k in ("predicted_close", "actual_close", "baseline_close"))
        r.update(p=p, a=a, b=b,
                 em=abs(p - a) / b,   # model error as a share of the last known price
                 ef=abs(b - a) / b,   # error of "the price stays the same"
                 moved=a != b, hit=a != b and (p > b) == (a > b) and p != b, up=a > b)
    return rows


class Agg:
    """Sums that every score below is built from, so groups and resamples add up exactly."""
    def __init__(self, rows=()):
        self.n = self.em = self.ef = self.moved = self.hit = self.up = 0
        for r in rows:
            self.n += 1
            self.em += r["em"]
            self.ef += r["ef"]
            self.moved += r["moved"]
            self.hit += r["hit"]
            self.up += r["up"]

    def __add__(self, o):
        s = Agg()
        for k in vars(s):
            setattr(s, k, getattr(self, k) + getattr(o, k))
        return s

    skill = property(lambda s: 1 - s.em / s.ef)          # above 0: better than "stays the same"
    hit_rate = property(lambda s: s.hit / s.moved)       # direction right, among targets that moved
    best_guess = property(lambda s: max(s.up, s.moved - s.up) / s.moved)  # always-up or always-down, whichever wins


def selftest():
    same = [dict(em=0.01, ef=0.01, moved=True, hit=True, up=True)] * 3
    assert Agg(same).skill == 0 and Agg(same).hit_rate == 1 and (Agg(same) + Agg(same)).n == 6
    worse = [dict(em=0.02, ef=0.01, moved=True, hit=False, up=False)]
    assert abs(Agg(worse).skill + 1) < 1e-12 and Agg(worse).best_guess == 1
    assert minutes("3m") == 3 and minutes("4h") == 240


def groups(rows, key):
    out = defaultdict(list)
    for r in rows:
        out[key(r)].append(r)
    return out


def frame_group(r):
    m = minutes(r["frame"])
    return "1 to 5 minute candles" if m <= 5 else "15 to 60 minute candles" if m <= 60 else "2 to 8 hour candles"


def horizon_group(r):
    return "next candle" if r["h"] == 1 else "candles 2 to 5 ahead" if r["h"] <= 5 else "candles 6 to 13 ahead"


def download(symbol, frame, start_ms, limit):
    for host in ("https://api.binance.com", "https://data-api.binance.vision"):
        url = f"{host}/api/v3/klines?symbol={symbol}&interval={frame}&startTime={start_ms}&limit={limit}"
        try:
            return json.loads(urllib.request.urlopen(url, timeout=30).read())
        except (OSError, ValueError):
            continue
    return None


def exchange_check(matched, fetch):
    """Compare saved baselines and outcomes with the exchange's own candles for a random sample of crypto forecasts."""
    by = groups([r for r in matched if r["market"] == "crypto"], lambda r: r["origin"])
    sample = random.Random(SEED).sample(sorted(by), min(SAMPLE_FORECASTS, len(by)))
    cache = json.loads(CANDLES.read_text()) if CANDLES.exists() else {}
    c = Counter()
    ms = lambda t: int(t.timestamp() * 1000)
    same = lambda x, y: x is not None and abs(x - y) <= 1e-9 * abs(y)
    for origin in sample:
        g = by[origin]
        step = timedelta(minutes=minutes(g[0]["frame"]))
        anchor = T(g[0]["target_start"]) - step * g[0]["h"]  # the last candle the model saw
        key = f"{g[0]['symbol']}|{g[0]['frame']}|{ms(anchor)}"
        if key not in cache and fetch:
            got = download(g[0]["symbol"], g[0]["frame"], ms(anchor), max(r["h"] for r in g) + 1)
            if got:
                cache[key] = [[k[0], k[4]] for k in got]  # open time, close
                CANDLES.write_text(json.dumps(cache))
            time.sleep(0.15)
        if key not in cache:
            c["no exchange data"] += 1
            continue
        close = {int(k[0]): float(k[1]) for k in cache[key]}
        c["forecasts"] += 1
        c["baseline ok"] += same(close.get(ms(anchor)), g[0]["b"])
        for r in g:
            c["outcomes"] += 1
            c["outcome ok"] += same(close.get(ms(T(r["target_start"]))), r["a"])
    return c


def main():
    selftest()
    rows = load()
    matched = [r for r in rows if r["status"] == "Matched"]
    pending = [r for r in rows if r["status"] != "Matched"]
    priced = [r for r in matched if "em" in r]  # accuracy needs prices; counts and timing use every scored target
    assert all(r["market"] == "stock" for r in matched if "em" not in r)
    assert not any(r[k] for r in rows if r["market"] == "stock" for k in ("predicted_close", "actual_close", "baseline_close"))
    total = Agg(priced)
    pct = lambda x: f"{100 * x:.1f}%"
    L = [f"# Numbers behind the audit (written by audit.py, seed {SEED})", "",
         f"Table: data/targets.csv, sha256 {hashlib.sha256(TABLE.read_bytes()).hexdigest()[:16]}",
         (f"Prices: {len(priced):,} of the {len(matched):,} scored targets carry prices, all of them crypto. "
          "The stock rows keep their timing and status only, so sections 3 to 6 are about the crypto targets."), ""]

    # 1. What the sample really is
    sym = Counter(r["symbol"] for r in matched)
    days = Counter(r["day"] for r in matched)
    top6, top2 = sum(n for _, n in sym.most_common(6)), sum(n for _, n in days.most_common(2))
    hours = groups(matched, lambda r: r["saved_at"][:13])
    L += ["## 1. Sample",
          f"- Targets in the table: {len(rows):,}; scored: {len(matched):,}; never scored: {len(pending):,}",
          f"- Forecasts behind the scored targets: {len({r['origin'] for r in matched}):,}",
          f"- Symbols: {len(sym)}; the 6 largest ({', '.join(s for s, _ in sym.most_common(6))}) hold {pct(top6 / len(matched))} of the scored targets",
          f"- Calendar days: {len(days)}; the 2 largest hold {pct(top2 / len(matched))}",
          f"- Distinct clock hours in which forecasts were saved: {len(hours)}",
          f"- Share on 1 to 5 minute candles: {pct(sum(frame_group(r).startswith('1 to 5') for r in matched) / len(matched))}", ""]

    # 2. Forward only: saved before the target, outcome read after it
    late = sum(T(r["saved_at"]) > T(r["target_start"]) for r in matched)
    early = sum(T(r["actual_observed_at"]) < T(r["target_end"]) for r in matched)
    margin = sorted((T(r["target_start"]) - T(r["saved_at"])).total_seconds() for r in matched)
    L += ["## 2. Forward only",
          f"- Scored targets saved after their candle had started: {late}",
          f"- Outcomes read before their candle had ended: {early}",
          f"- Shortest gap between saving and candle start: {margin[0]:.0f} seconds; median {margin[len(margin) // 2] / 60:.0f} minutes",
          f"- Scored targets saved less than 60 seconds before their candle started: {sum(x < 60 for x in margin)}",
          f"- 'Next candle' targets: {sum(r['h'] == 1 for r in matched)} scored of {sum(r['h'] == 1 for r in rows)} in the table", ""]

    # 3. Baseline: one "last known price" per forecast
    mixed = sum(len({r["b"] for r in g}) > 1 for g in groups(priced, lambda r: r["origin"]).values())
    L += ["## 3. Baseline", f"- Forecasts whose targets use more than one baseline price: {mixed}", ""]

    # 4. Saved prices against the exchange
    c = exchange_check(priced, "--fetch" in sys.argv)
    L += ["## 4. Saved prices against the exchange (random sample of crypto forecasts, Binance spot candles)",
          f"- Forecasts checked: {c['forecasts']} of {min(SAMPLE_FORECASTS, len({r['origin'] for r in matched if r['market'] == 'crypto'}))} sampled (no exchange data: {c['no exchange data']})",
          f"- Baseline equals the exchange close of the last candle the model saw: {c['baseline ok']} of {c['forecasts']}",
          f"- Outcome equals the exchange close of the target candle: {c['outcome ok']} of {c['outcomes']}", ""]

    # 5. The headline, recomputed
    line = lambda name, a: f"- {name}: skill {a.skill:+.3f}, direction right {pct(a.hit_rate)} against {pct(a.best_guess)} for the best constant guess ({a.n:,} targets)"
    L += ["## 5. Headline recomputed",
          "Skill = 1 - (sum of model errors / sum of 'stays the same' errors), errors as a share of the last known price.",
          line("All scored targets with prices (crypto)", total)]
    for key in (frame_group, horizon_group):
        L += [line(k, Agg(g)) for k, g in sorted(groups(priced, key).items())]
    per_symbol = {s: Agg(g) for s, g in groups(priced, lambda r: r["symbol"]).items()}
    big = [s for s, _ in sym.most_common(6)]
    btc = Agg([r for r in priced if r["symbol"].startswith("BTC")])
    raw = lambda rs: sum(abs(r["b"] - r["a"]) for r in rs)
    cells = sorted(Agg(g).skill for g in groups(priced, lambda r: (r["symbol"], r["frame"])).values() if Agg(g).ef)
    raw_skill = 1 - sum(abs(r["p"] - r["a"]) for r in priced) / raw(priced)
    L += [f"- Symbols with skill above zero: {sum(a.skill > 0 for a in per_symbol.values())} of {len(per_symbol)}; among the 6 largest: {sum(per_symbol[s].skill > 0 for s in big)} of 6",
          f"- Targets that did not move at all (left out of the direction count): {total.n - total.moved}",
          f"- Skill with errors pooled in raw price units instead: {raw_skill:+.3f}; there the BTC pairs carry {pct(raw([r for r in priced if r['symbol'].startswith('BTC')]) / raw(priced))} of the baseline error with {pct(btc.n / total.n)} of the targets",
          f"- Middle skill over the {len(cells)} symbol-and-candle-size groups: {cells[len(cells) // 2]:+.3f}", ""]

    # 6. How sure: the targets are not independent
    rng = random.Random(SEED)
    parts = [Agg(g) for g in groups(priced, lambda r: r["saved_at"][:13]).values()]
    skills, edges = [], []
    for _ in range(RESAMPLES):
        s = Agg()
        for a in rng.choices(parts, k=len(parts)):
            s = s + a
        skills.append(s.skill)
        edges.append(s.hit_rate - s.best_guess)
    skills.sort()
    edges.sort()
    lo, hi = int(0.025 * RESAMPLES), int(0.975 * RESAMPLES) - 1
    by_day = {d: Agg(g) for d, g in sorted(groups(priced, lambda r: r["day"]).items())}
    without = [Agg([r for r in priced if r["day"] != d]).skill for d in by_day]
    L += ["## 6. How sure",
          f"- 95% range of the skill when whole save-hours are resampled ({len(parts)} hours, {RESAMPLES:,} resamples): {skills[lo]:+.3f} to {skills[hi]:+.3f}",
          f"- Same for direction right minus best constant guess: {100 * edges[lo]:+.1f} to {100 * edges[hi]:+.1f} percentage points",
          f"- Share of resamples with skill above zero: {pct(sum(s > 0 for s in skills) / RESAMPLES)}",
          "- Skill per day: " + "; ".join(f"{d} {a.skill:+.3f} ({a.n:,})" for d, a in by_day.items()),
          f"- Skill with any one day left out: {min(without):+.3f} to {max(without):+.3f}", ""]

    # 7. What was never scored
    miss = Counter(r["market"] for r in pending)
    have = Counter(r["market"] for r in matched)
    L += ["## 7. Never scored"] + [f"- {m}: {miss[m]:,} of {miss[m] + have[m]:,} targets ({pct(miss[m] / (miss[m] + have[m]))})" for m in sorted(have)]

    assert sum(a.n for a in per_symbol.values()) == total.n == sum(a.n for a in parts)
    (HERE / "numbers.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
