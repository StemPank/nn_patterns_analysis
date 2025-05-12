import numpy as np
import matplotlib.pyplot as plt
import random

def generate_ascending_triangle(length=50, noise=0.001, scale=1.0):
    lows = np.linspace(scale * 0.95, scale * 1.02, length)
    highs = np.full(length, scale * 1.05)  # горизонтальное сопротивление
    closes = []

    for i in range(length):
        close = random.uniform(lows[i], highs[i])
        closes.append(close)
    return closes
def generate_bear_flag(length=50, noise=0.001, scale=1.0):
    """Флаг нисходящий (Bear Flag)"""
    trend_len = length // 3
    flag_len = length - trend_len
    trend = np.linspace(scale * 1.025, scale * 0.975, trend_len)
    flag = np.linspace(scale * 0.975, scale * 1.000, flag_len)
    closes = np.concatenate([trend, flag])
    closes = [c * (1 + random.uniform(-noise, noise)) for c in closes]
    return closes
def generate_bull_flag(length=50, noise=0.001, scale=1.0):
    """Флаг восходящий (Bull Flag)"""
    trend_len = length // 3
    flag_len = length - trend_len
    trend = np.linspace(scale * (0.975 - noise), scale * (1.025 + noise), trend_len)
    flag = np.linspace(scale * (1.025 + noise), scale * (1.015 - noise), flag_len)
    closes = np.concatenate([trend, flag])
    closes = [c * (1 + random.uniform(-noise, noise)) for c in closes]
    return closes


def generate_ascending_wedge(length=50, noise=0.001, scale=1.0):
    """Восходящий клин (Ascending Wedge)"""
    lows = np.linspace(scale * (0.975 - noise), scale * (1.02 + noise), length)
    highs = np.linspace(scale * 1.00, scale * (1.025 + noise), length)
    closes = [random.uniform(
        lows[i] * (1 + random.uniform(-noise, noise)),
        highs[i] * (1 + random.uniform(-noise, noise))
    ) for i in range(length)]
    return closes

def generate_descending_wedge(length=50, noise=0.001, scale=1.0):
    """Нисходящий клин (Descending Wedge)"""
    highs = np.linspace(scale * (1.025 + noise), scale * (0.98 - noise), length)
    lows = np.linspace(scale * 1.00, scale * (0.975 - noise), length)
    closes = [random.uniform(
        lows[i] * (1 + random.uniform(-noise, noise)),
        highs[i] * (1 + random.uniform(-noise, noise))
    ) for i in range(length)]
    return closes


def to_ohlcv(close_series, spread=0.005):
    ohlcv = []
    for i, close in enumerate(close_series):
        open_ = close_series[i - 1] if i > 0 else close
        high = max(open_, close) * (1 + random.uniform(0, spread))
        low = min(open_, close) * (1 - random.uniform(0, spread))
        volume = random.uniform(10, 100)
        ohlcv.append((open_, high, low, close, volume))
    return ohlcv


# Сгенерируем данные
close_series = generate_descending_wedge()
ohlcv_data = to_ohlcv(close_series)

# Извлечём данные для графика
times = list(range(len(ohlcv_data)))
opens, highs, lows, closes, volumes = zip(*ohlcv_data)

# Построим график
plt.figure(figsize=(12, 6))
plt.plot(times, closes, label='Close', color='blue')
plt.plot(times, highs, label='High', linestyle='--', color='orange')
plt.plot(times, lows, label='Low', linestyle='--', color='green')
plt.fill_between(times, lows, highs, color='gray', alpha=0.1)
plt.title("Сгенерированный Восходящий Треугольник (OHLC)")
plt.xlabel("Время (индекс свечи)")
plt.ylabel("Цена")
plt.legend()
plt.grid(True)
plt.show()