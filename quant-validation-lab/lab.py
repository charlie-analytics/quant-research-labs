"""Offline retrospective event study. No network, orders, or production imports."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "0.1.1"
COLS = ["open", "high", "low", "close", "volume"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate(frame):
    if frame.index.names != ["symbol", "ts"]:
        raise ValueError("Expected symbol/ts MultiIndex")
    if frame.empty or any(c not in frame for c in COLS):
        raise ValueError("Missing OHLCV data")
    d = frame[COLS].copy()
    if d.index.duplicated().any():
        raise ValueError("Duplicate symbol/date")
    dates = pd.DatetimeIndex(d.index.get_level_values("ts"))
    if str(dates.tz) != "UTC" or not dates.equals(dates.normalize()):
        raise ValueError("Daily UTC timestamps required")
    if not np.isfinite(d.to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite OHLCV")
    if (d[["open", "high", "low", "close"]] <= 0).any().any() or (d.volume < 0).any():
        raise ValueError("Invalid price/volume")
    if ((d.high < d[["open", "close", "low"]].max(axis=1)) |
            (d.low > d[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("Inconsistent OHLC")
    return d.sort_index()


def panels(d):
    # Explicit daily grid: missing sessions stay missing; never forward-fill.
    dates = pd.date_range(d.index.get_level_values("ts").min(),
                          d.index.get_level_values("ts").max(), freq="D")
    return {c: d[c].unstack("symbol").reindex(dates).sort_index(axis=1) for c in COLS}


def build_events(d, horizon=5, lookback=20, stride=7, min_universe=8):
    """Each event is a long-only hypothetical holding, never a portfolio equity curve.

    Signal uses the completed date-t candle. Entry is t+1 open; exit t+1+h close.
    A UTC daily label denotes candle OPEN, so exit is available the following day.
    Benchmark consists of assets eligible from information at signal time only.
    If ANY benchmark member lacks a holding-period bar, reject the entire date.
    """
    if min(horizon, lookback, stride, min_universe) < 1:
        raise ValueError("Positive experiment parameters required")
    p = panels(d); close = p["close"]; op = p["open"]
    rows, rejects = [], []
    for t in range(lookback, len(close), stride):
        signal_date = close.index[t]
        known = close.iloc[t-lookback:t+1]
        eligible = list(known.columns[known.notna().all()])
        if len(eligible) < min_universe:
            rejects.append({"signal_date": signal_date, "reason": "insufficient_known_universe"})
            continue
        exit_i = t + 1 + horizon
        if exit_i >= len(close):
            rejects.append({"signal_date": signal_date, "reason": "unresolved_outcome"})
            continue
        # Requiring the entire declared holding path prevents hidden interior gaps.
        path = close.iloc[t+1:exit_i+1][eligible]
        if path.isna().any().any() or op.iloc[t+1][eligible].isna().any():
            rejects.append({"signal_date": signal_date, "reason": "incomplete_fixed_benchmark"})
            continue
        entry = op.iloc[t+1][eligible]
        gross = (close.iloc[exit_i][eligible] / entry - 1.0) * 100
        benchmark = float(gross.mean())
        scores = (known.iloc[-1][eligible] / known.iloc[0][eligible] - 1.0) * 100
        for symbol in eligible:
            rows.append({"symbol": symbol, "signal_date": signal_date,
                         "signal_available": signal_date + pd.Timedelta(days=1),
                         "entry_date": close.index[t+1], "exit_date": close.index[exit_i],
                         "exit_available": close.index[exit_i] + pd.Timedelta(days=1),
                         "score": float(scores[symbol]), "entry_price": float(entry[symbol]),
                         "exit_price": float(close.iloc[exit_i][symbol]),
                         "gross_pct": float(gross[symbol]), "benchmark_gross_pct": benchmark,
                         "benchmark_n": len(eligible)})
    return pd.DataFrame(rows), pd.DataFrame(rejects, columns=["signal_date", "reason"])


def select(rows, sign, top_n):
    if rows.empty:
        return rows.copy()
    # Stable symbol tie-break makes equal scores reproducible.
    return (rows.assign(rank_score=rows.score * sign)
            .sort_values(["signal_date", "rank_score", "symbol"], ascending=[True, False, True])
            .groupby("signal_date", sort=True).head(top_n).drop(columns="rank_score"))


def fit(train, top_n, cost_bps):
    if train.empty:
        raise ValueError("Empty training set")
    def value(sign):
        x = select(train, sign, top_n)
        return float((x.gross_pct - x.benchmark_gross_pct - cost_bps / 100).mean())
    values = {1: value(1), -1: value(-1)}
    # Tie favors momentum; negative training results remain eligible and visible.
    sign = 1 if values[1] >= values[-1] else -1
    return sign, values


def evaluate(events, start, end, cost_bps=25.0, top_n=3, min_train_dates=20):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start.tzinfo is None: start = start.tz_localize("UTC")
    if end.tzinfo is None: end = end.tz_localize("UTC")
    if end <= start or cost_bps < 0 or top_n < 1:
        raise ValueError("Invalid fold/cost parameters")
    # No label touching the evaluation boundary may influence fitting.
    train = events[(events.signal_available < start) & (events.exit_available < start)]
    boundary = events[(events.signal_available < start) & (events.exit_available >= start)]
    test = events[(events.signal_available >= start) & (events.signal_available < end)]
    # Outcome must also finish inside the declared evaluation period.
    test = test[test.exit_available <= end]
    if train.signal_date.nunique() < min_train_dates or test.empty:
        return None, {"start": start.isoformat(), "end": end.isoformat(), "status": "insufficient_data",
                      "train_dates": int(train.signal_date.nunique()), "purged_rows": len(boundary)}
    sign, train_scores = fit(train, top_n, cost_bps)
    picked = select(test, sign, top_n).copy()
    picked["fold"] = start.isoformat()
    picked["cost_bps"] = cost_bps
    picked["net_pct"] = picked.gross_pct - cost_bps / 100.0
    picked["gross_excess_pct"] = picked.gross_pct - picked.benchmark_gross_pct
    picked["net_excess_vs_gross_benchmark_pct"] = picked.net_pct - picked.benchmark_gross_pct
    # A tradable benchmark with identical assumed round-trip cost is also shown.
    picked["benchmark_net_pct"] = picked.benchmark_gross_pct - cost_bps / 100.0
    picked["net_excess_vs_net_benchmark_pct"] = picked.net_pct - picked.benchmark_net_pct
    fold = {"start": start.isoformat(), "end": end.isoformat(), "status": "complete",
            "ranking_sign": sign, "train_dates": int(train.signal_date.nunique()),
            "train_last_exit_available": train.exit_available.max().isoformat(),
            "purged_rows": len(boundary), "training_candidate_mean_excess_pp": train_scores,
            "test_dates": int(picked.signal_date.nunique()), "test_events": len(picked)}
    return picked, fold


def summarize(picked):
    # Date-basket averages: equal dates, rather than pooled symbol-dependent weights.
    cols = ["gross_pct", "net_pct", "benchmark_gross_pct", "benchmark_net_pct",
            "net_excess_vs_gross_benchmark_pct", "net_excess_vs_net_benchmark_pct"]
    bydate = picked.groupby(["fold", "signal_date"])[cols].mean()
    out = {"events": len(picked), "evaluation_dates": len(bydate),
           "mean_date_basket_pct": {c: float(bydate[c].mean()) for c in cols},
           "median_date_basket_net_pct": float(bydate.net_pct.median()),
           "positive_date_basket_net_fraction": float((bydate.net_pct > 0).mean()),
           "worst_date_basket_net_pct": float(bydate.net_pct.min())}
    out["cost_sensitivity_mean_net_pct"] = {
        str(bps): float((bydate.gross_pct - bps / 100).mean()) for bps in (0, 25, 50, 100)}
    return out


def run(input_path, output_path, eval_years, as_of="2026-10-17"):
    input_path, output_path = Path(input_path).resolve(), Path(output_path).resolve()
    if output_path.exists(): raise ValueError("Output must be a NEW directory")
    digest = sha256(input_path)
    d = validate(pd.read_parquet(input_path))
    # Drop a potentially incomplete current daily candle, based on explicit UTC clock.
    today = pd.Timestamp(as_of, tz="UTC").normalize()
    incomplete = d.index.get_level_values("ts") >= today
    omitted = int(incomplete.sum()); d = d.loc[~incomplete]
    events, rejected = build_events(d)
    if events.empty: raise ValueError("No complete events")
    results, folds = [], []
    last_available = d.index.get_level_values("ts").max() + pd.Timedelta(days=1)
    for year in eval_years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = min(pd.Timestamp(f"{year+1}-01-01", tz="UTC"), last_available)
        if end <= start: continue
        picked, fold = evaluate(events, start, end)
        folds.append(fold)
        if picked is not None: results.append(picked)
    if not results: raise ValueError("No eligible evaluation folds")
    picked = pd.concat(results, ignore_index=True)
    if sha256(input_path) != digest: raise ValueError("Source changed during evaluation")
    summary = summarize(picked)
    manifest = {"version": VERSION, "classification": "RETROSPECTIVE_VALIDATION_NOT_UNTOUCHED_OOS",
                "as_of_utc_exclusive_daily_date": today.isoformat(),
                "input": {"path": str(input_path), "sha256": digest, "rows": len(d),
                          "symbols": d.index.get_level_values("symbol").nunique(),
                          "from": d.index.get_level_values("ts").min().isoformat(),
                          "to": d.index.get_level_values("ts").max().isoformat(),
                          "incomplete_current_rows_omitted": omitted},
                "code_sha256": sha256(__file__), "dependencies": {"pandas": pd.__version__, "numpy": np.__version__},
                "experiment": {"lookback_days": 20, "horizon_days_entry_to_exit": 5,
                               "entry": "next daily open", "exit": "entry+5 days daily close",
                               "signal_stride_days": 7, "top_n": 3, "min_known_universe": 8,
                               "training": "expanding; high vs low momentum rank, fixed tie rule",
                               "cost_bps_round_trip": 25, "eval_years": eval_years},
                "limitations": ["Reused history and new design are retrospective, not an untouched holdout.",
                                "Cache provenance says Binance spot/USDT; no independent upstream audit.",
                                "Universe is cache membership; delisted coverage and survivorship unresolved.",
                                "Costs are assumptions, not measured spread/slippage or borrow/funding.",
                                "Event study; no compounded portfolio equity, Sharpe or live P&L.",
                                "A 5-day open-to-close outcome spans six daily candles.",
                                "Incomplete benchmark dates rejected in full, possibly inducing missingness bias.",
                                "No significance or confidence intervals claimed; dates/assets dependent.",
                                "Snapshot includes completed rows only; no data refresh or network fallback."]}
    output_path.mkdir(parents=True, exist_ok=False)
    events.to_csv(output_path / "candidate_events.csv", index=False)
    picked.to_csv(output_path / "events.csv", index=False)
    rejected.to_csv(output_path / "rejected_dates.csv", index=False)
    pd.DataFrame(folds).to_csv(output_path / "folds.csv", index=False)
    (output_path / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    (output_path / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    report = ("# Retrospective validation lab\n\nThis is a hypothetical long-only event study, not live trading or an untouched holdout.\n\n"
              "Every year fits high-versus-low 20-day momentum ranking using only outcomes available before January 1. "
              "Signals enter next open and exit five dates later at close. Benchmark assets are fixed at signal time, "
              "use matching price clocks, and receive equal weights. Missing holding paths reject the entire date.\n\n"
              "Costs: 25 basis points per round trip; 0/25/50/100-basis-point sensitivity keeps selection fixed. "
              "No spread, impact, intraday execution or HFT claim. Event returns are not compounded as account equity.\n\n"
              "## Results\n\n```json\n" + json.dumps(summary, indent=2) + "\n```\n\n## Limits\n\n" +
              "\n".join("- "+x for x in manifest["limitations"]) + "\n")
    (output_path / "report.md").write_text(report)
    hashes = {p.name: sha256(p) for p in sorted(output_path.iterdir()) if p.is_file()}
    (output_path / "output_hashes.json").write_text(json.dumps(hashes, indent=2)+"\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--eval-years", default="2022,2023,2024,2025,2026")
    parser.add_argument("--as-of", required=True, help="UTC date; candles at/after this date excluded")
    args = parser.parse_args()
    print(json.dumps(run(args.input, args.output, sorted(set(map(int, args.eval_years.split(",")))),args.as_of), indent=2))
