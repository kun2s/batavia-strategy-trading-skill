"""Auditable, no-look-ahead backtest engine shared by every Batavia candidate."""
from __future__ import annotations

from dataclasses import dataclass
import csv

from batavia.indicators import atr_series, bollinger, ema, rsi, trend_score, vol_state
from batavia.regime import (
    EUPHORIA, EXTREME_FEAR, RANGING, RISK_OFF, TRENDING_UP,
    Signals, classify,
)

WARMUP = 50
FEE = 0.0005
STOP_LOSS_PCT = 0.025
TAKE_PROFIT_PCT = 0.08
MAX_HOLD_BARS = 72
POLICIES = (
    "router", "trend_cash", "sentiment_momentum", "momentum",
    "mean_reversion", "buy_hold", "cash",
)


@dataclass
class MarketData:
    timestamps: list[int]
    opens: list[float]
    highs: list[float]
    lows: list[float]
    closes: list[float]
    fear_greed: list[float | None]
    funding_stress: list[float | None]

    def __len__(self):
        return len(self.closes)


def load_market_csv(path):
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty market CSV: {path}")
    timestamps, opens, highs, lows, closes, fear, funding = [], [], [], [], [], [], []
    previous_close = None
    for index, row in enumerate(rows):
        close = float(row["close"])
        timestamp = int(float(row.get("timestamp") or index * 3_600_000))
        open_price = float(row.get("open") or previous_close or close)
        high = float(row["high"])
        low = float(row["low"])
        if min(open_price, high, low, close) <= 0:
            raise ValueError(f"non-positive OHLC value at row {index + 2}: {path}")
        if high < max(open_price, close) or low > min(open_price, close) or low > high:
            raise ValueError(f"invalid OHLC bounds at row {index + 2}: {path}")
        timestamps.append(timestamp)
        opens.append(open_price)
        highs.append(high); lows.append(low); closes.append(close)
        raw_fear = row.get("fear_greed", "")
        fear.append(float(raw_fear) if raw_fear not in (None, "") else None)
        raw_funding = row.get("funding_stress", row.get("funding", ""))
        funding.append(float(raw_funding) if raw_funding not in (None, "") else None)
        previous_close = close
    if timestamps != sorted(set(timestamps)):
        raise ValueError(f"timestamps must be strictly increasing and unique: {path}")
    return MarketData(timestamps, opens, highs, lows, closes, fear, funding)


def align_market_data(datasets):
    """Align every asset to the exact intersection of available timestamps."""
    if not datasets:
        raise ValueError("at least one market dataset is required")
    common = set.intersection(*(set(data.timestamps) for data in datasets.values()))
    ordered = sorted(common)
    if len(ordered) <= WARMUP + 6:
        raise ValueError("not enough common timestamp bars across assets")
    if any(current - previous != 3_600_000 for previous, current in zip(ordered, ordered[1:])):
        raise ValueError("common market timestamp grid must be continuous hourly data")
    aligned = {}
    fields = ("opens", "highs", "lows", "closes", "fear_greed", "funding_stress")
    for symbol, data in datasets.items():
        positions = {timestamp: index for index, timestamp in enumerate(data.timestamps)}
        selected = {field: [getattr(data, field)[positions[timestamp]] for timestamp in ordered]
                    for field in fields}
        aligned[symbol] = MarketData(ordered, **selected)
    return aligned


def indicator_frame(data):
    fast = ema(data.closes, 20)
    slow = ema(data.closes, 50)
    rsis = rsi(data.closes, 14)
    _, _, lower = bollinger(data.closes, 20, 2)
    atrs = atr_series(data.highs, data.lows, data.closes, 14)
    trend = [trend_score(data.closes[i], fast[i], slow[i]) for i in range(len(data))]
    signals = [Signals(
        fear_greed=data.fear_greed[i], trend_score=trend[i],
        vol_state=vol_state(atrs[i] / data.closes[i]) if atrs[i] is not None and data.closes[i] else None,
        funding_stress=data.funding_stress[i],
    ) for i in range(len(data))]
    raw = [classify(signal)[0] for signal in signals]
    confirmed, counts = confirm_regimes(raw, signals)
    return {"ema20": fast, "ema50": slow, "rsi": rsis, "lower": lower,
            "atr": atrs, "signals": signals, "raw": raw,
            "confirmed": confirmed, "confirmation_count": counts}


def confirm_regimes(raw_labels, signals, bars=3):
    current = RANGING
    pending = None
    streak = 0
    labels, counts = [], []
    for raw, signal in zip(raw_labels, signals):
        immediate = raw == EUPHORIA or (signal.fear_greed is not None and signal.fear_greed <= EXTREME_FEAR)
        if immediate:
            current, pending, streak = raw, None, 1
        elif raw == current:
            pending, streak = None, min(bars, streak + 1)
        else:
            if raw == pending:
                streak += 1
            else:
                pending, streak = raw, 1
            if streak >= bars:
                current, pending, streak = raw, None, bars
        labels.append(current); counts.append(streak)
    return labels, counts


def _active_style(policy, frame, index):
    confirmed = frame["confirmed"][index]
    raw = frame["raw"][index]
    if policy in ("router", "trend_cash", "sentiment_momentum") and frame["signals"][index].fear_greed is None:
        return "cash"
    if policy == "router":
        if confirmed == TRENDING_UP:
            return "momentum"
        if confirmed == RANGING:
            return "mean_reversion"
        return "cash"
    if policy == "trend_cash":
        return "momentum" if confirmed == TRENDING_UP else "cash"
    if policy == "sentiment_momentum":
        signal = frame["signals"][index]
        fear_veto = signal.fear_greed is not None and signal.fear_greed <= EXTREME_FEAR
        return "cash" if raw == EUPHORIA or fear_veto else "momentum"
    if policy in ("momentum", "mean_reversion", "cash"):
        return policy
    raise ValueError(f"unknown policy: {policy}")


def _entry_signal(style, frame, data, index):
    if index < 1:
        return False
    if style == "momentum":
        current, previous = frame["ema20"][index], frame["ema20"][index - 1]
        return (current is not None and previous is not None and
                data.closes[index - 1] <= previous and data.closes[index] > current)
    if style == "mean_reversion":
        value, lower = frame["rsi"][index], frame["lower"][index]
        return value is not None and lower is not None and value < 30 and data.closes[index] <= lower
    return False


def _signal_exit(policy, position_style, frame, index):
    style = _active_style(policy, frame, index)
    if policy in ("router", "trend_cash", "sentiment_momentum") and style != position_style:
        return "policy_invalidation"
    if position_style == "mean_reversion":
        value = frame["rsi"][index]
        return "rsi_exit" if value is not None and value > 55 else None
    return None


def _position_fraction(style, frame, data, index):
    atr = frame["atr"][index]
    atr_fraction = atr / data.closes[index] if atr is not None and data.closes[index] else 0.02
    return max(0.05, min(0.25, 0.15 * 0.02 / max(atr_fraction, 1e-9)))


def run(data, policy="router", *, start=None, end=None):
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    frame = indicator_frame(data)
    start = max(WARMUP, WARMUP if start is None else start)
    end = min(len(data), len(data) if end is None else end)
    if end - start < 2:
        raise ValueError("backtest window must contain at least two evaluated bars")
    if policy == "cash":
        return _empty_metrics(data, frame, start, end)
    if policy == "buy_hold":
        return _buy_hold(data, frame, start, end)

    cash = 1.0
    position = None
    trades = []
    equity_curve = []
    peak = 1.0
    max_drawdown = 0.0
    exposure_bars = 0
    turnover = 0.0
    regime_bars = {TRENDING_UP: 0, RANGING: 0, EUPHORIA: 0, RISK_OFF: 0}

    def equity(price):
        return cash + (position["units"] * price if position else 0.0)

    def close_position(price, reason, bar_index):
        nonlocal cash, position, turnover
        gross = position["units"] * price
        fee = gross * FEE
        cash += gross - fee
        turnover += gross
        entry_value = position["entry_value"]
        net_value = gross - fee
        trades.append({
            "entry_bar": position["entry_bar"], "exit_bar": bar_index,
            "style": position["style"], "reason": reason,
            "return_pct": (net_value / entry_value - 1) * 100,
        })
        position = None

    def apply_intrabar(bar_index):
        if not position:
            return
        open_price, high, low = data.opens[bar_index], data.highs[bar_index], data.lows[bar_index]
        if open_price <= position["stop"]:
            close_position(open_price, "stop_gap", bar_index)
        elif open_price >= position["target"]:
            close_position(position["target"], "take_profit", bar_index)
        elif low <= position["stop"]:
            close_position(position["stop"], "stop_loss", bar_index)
        elif high >= position["target"]:
            close_position(position["target"], "take_profit", bar_index)

    for i in range(start, end):
        previous = i - 1
        regime_bars[frame["confirmed"][previous]] += 1
        exited_at_open = False
        exposed_this_bar = position is not None
        if position:
            reason = _signal_exit(policy, position["style"], frame, previous)
            if reason or i - position["entry_bar"] >= position["max_hold"]:
                close_position(data.opens[i], reason or "timeout", i)
                exited_at_open = True

        position_before_intrabar = position is not None
        if position:
            apply_intrabar(i)
        exited_intrabar = position_before_intrabar and position is None

        if not position and not exited_at_open and not exited_intrabar:
            style = _active_style(policy, frame, previous)
            if _entry_signal(style, frame, data, previous):
                fraction = _position_fraction(style, frame, data, previous)
                total = cash
                allocation = total * fraction
                entry_fee = allocation * FEE
                units = (allocation - entry_fee) / data.opens[i]
                cash -= allocation
                turnover += allocation
                position = {
                    "style": style, "units": units, "entry": data.opens[i],
                    "entry_value": allocation, "entry_bar": i,
                    "stop": data.opens[i] * (1 - STOP_LOSS_PCT),
                    "target": data.opens[i] * (1 + TAKE_PROFIT_PCT),
                    "max_hold": MAX_HOLD_BARS,
                }
                exposed_this_bar = True
                apply_intrabar(i)

        if exposed_this_bar:
            exposure_bars += 1
        marked = equity(data.closes[i])
        equity_curve.append(marked)
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak if peak else 0.0)

    if position:
        close_position(data.closes[end - 1], "final_bar", end - 1)
        marked = cash
        equity_curve[-1] = marked
        peak = max(peak, marked)
        max_drawdown = max(max_drawdown, (peak - marked) / peak if peak else 0.0)

    final_equity = equity_curve[-1]
    wins = sum(1 for trade in trades if trade["return_pct"] > 0)
    return {
        "policy": policy, "bars": end - start,
        "total_return_pct": round((final_equity - 1) * 100, 4),
        "max_drawdown_pct": round(max_drawdown * 100, 4),
        "return_over_drawdown": round((final_equity - 1) / max_drawdown, 4) if max_drawdown else 0.0,
        "trades": len(trades),
        "win_rate_pct": round(wins / len(trades) * 100, 2) if trades else 0.0,
        "exposure_pct": round(exposure_bars / (end - start) * 100, 2),
        "turnover_x": round(turnover, 4),
        "regime_bars": regime_bars,
        "exits": _tally(trade["reason"] for trade in trades),
        "trades_detail": trades,
    }


def _empty_metrics(data, frame, start, end):
    regimes = _tally(frame["confirmed"][i - 1] for i in range(start, end))
    return {"policy": "cash", "bars": end - start, "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0, "return_over_drawdown": 0.0, "trades": 0,
            "win_rate_pct": 0.0, "exposure_pct": 0.0, "turnover_x": 0.0,
            "regime_bars": regimes, "exits": {}, "trades_detail": []}


def _buy_hold(data, frame, start, end):
    entry, exit_price = data.opens[start], data.closes[end - 1]
    units = (1 - FEE) / entry
    curve = [units * data.closes[i] for i in range(start, end)]
    gross_exit = units * exit_price
    curve[-1] *= (1 - FEE)
    peak, drawdown = 1.0, 0.0
    for value in curve:
        peak = max(peak, value); drawdown = max(drawdown, (peak - value) / peak)
    ret = curve[-1] - 1
    return {"policy": "buy_hold", "bars": end - start,
            "total_return_pct": round(ret * 100, 4),
            "max_drawdown_pct": round(drawdown * 100, 4),
            "return_over_drawdown": round(ret / drawdown, 4) if drawdown else 0.0,
            "trades": 1, "win_rate_pct": 100.0 if ret > 0 else 0.0,
            "exposure_pct": 100.0, "turnover_x": round(1 + gross_exit, 4),
            "regime_bars": _tally(frame["confirmed"][i - 1] for i in range(start, end)),
            "exits": {"final_bar": 1}, "trades_detail": []}


def _tally(values):
    result = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def chronological_windows(length, warmup=WARMUP, count=3):
    if count <= 0:
        raise ValueError("window count must be positive")
    usable = length - warmup
    width = usable // count
    if width < 2:
        raise ValueError("not enough bars for chronological windows")
    return [(warmup + i * width, length if i == count - 1 else warmup + (i + 1) * width)
            for i in range(count)]
