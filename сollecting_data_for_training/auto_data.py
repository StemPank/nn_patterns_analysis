import sqlite3
import numpy as np
import random
from datetime import datetime, timedelta


from db_pattern_detection_app import MainDatabase
from loggings import LoggerManager

logger = LoggerManager().get_named_logger("pattern_auto")
data_base = MainDatabase()

def generate_symmetric_triangle(length=50, noise=0.001, scale=1.0):
    """Симметричный треугольник (Symmetric Triangle)"""
    half_len = length // 2
    highs = np.linspace(scale * (1.025 + noise), scale * (1.00 + noise), length)
    lows = np.linspace(scale * (0.975 - noise), scale * (1.00 - noise), length)
    closes = []

    for i in range(length):
        close = random.uniform(lows[i], highs[i])
        closes.append(close)
    return closes

def generate_ascending_triangle(length=50, noise=0.001, scale=1.0):
    """Восходящий треугольник (Ascending Triangle)"""
    lows = np.linspace(scale * (0.975 - noise), scale * (1.01 + noise), length)
    highs = np.full(length, scale * (1.025 + noise))  # горизонтальное сопротивление
    closes = []

    for i in range(length):
        close = random.uniform(lows[i], highs[i])
        closes.append(close)
    return closes

def generate_descending_triangle(length=50, noise=0.001, scale=1.0):
    """Нисходящий треугольник (Descending Triangle)"""
    highs = np.linspace(scale * (1.025 + noise), scale * (0.99 - noise), length)  # нисходящее сопротивление
    lows = np.full(length, scale * (0.975 + noise))  # горизонтальная поддержка
    closes = []

    for i in range(length):
        close = random.uniform(lows[i], highs[i])
        closes.append(close)
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

def generate_bull_flag(length=50, noise=0.001, scale=1.0):
    """Флаг восходящий (Bull Flag)"""
    trend_len = length // 3
    flag_len = length - trend_len
    trend = np.linspace(scale * (0.975 - noise), scale * (1.025 + noise), trend_len)
    flag = np.linspace(scale * (1.025 + noise), scale * (1.015 - noise), flag_len)
    closes = np.concatenate([trend, flag])
    closes = [c * (1 + random.uniform(-noise, noise)) for c in closes]
    return closes

def generate_bear_flag(length=50, noise=0.001, scale=1.0):
    """Флаг нисходящий (Bear Flag)"""
    trend_len = length // 3
    flag_len = length - trend_len
    trend = np.linspace(scale * (1.025 + noise), scale * (0.975 - noise), trend_len)
    flag = np.linspace(scale * (0.975 - noise), scale * (1.000 + noise), flag_len)
    closes = np.concatenate([trend, flag])
    closes = [c * (1 + random.uniform(-noise, noise)) for c in closes]
    return closes

def to_ohlcv(close_series, spread=0.005):
    """Добавляет остальные данные свечи"""
    ohlcv = []
    for i, close in enumerate(close_series):
        open_ = close_series[i - 1] if i > 0 else close
        high = max(open_, close) * (1 + random.uniform(0, spread))
        low = min(open_, close) * (1 - random.uniform(0, spread))
        volume = random.uniform(10, 100)
        ohlcv.append((open_, high, low, close, volume))
    return ohlcv

def smooth_transition(from_close, target_closes, steps, spread=0.005):
    """Плавно возвращаемся к реальному графику"""
    transition = []
    for i in range(steps):
        t = i / steps
        close = (1 - t) * from_close + t * target_closes[i]
        open_ = close if i == 0 else transition[-1][3]  # open = prev close
        high = max(open_, close) * (1 + random.uniform(0, spread))
        low = min(open_, close) * (1 - random.uniform(0, spread))
        volume = random.uniform(10, 100)
        transition.append((open_, high, low, close, volume))
    return transition


# Все доступные паттерны
PATTERN_GENERATORS = {
    "ascending_triangle": generate_ascending_triangle,
    "descending_triangle": generate_descending_triangle,
    "symmetric_triangle": generate_symmetric_triangle,
    "ascending_wedge": generate_ascending_wedge,
    "descending_wedge": generate_descending_wedge,
    "bull_flag": generate_bull_flag,
    "bear_flag": generate_bear_flag,
}

def generate_random_pattern(length=50, noise=0.001, scale=1.0):
    """Выберает случайный паттерн для вставки"""
    pattern_name = random.choice(list(PATTERN_GENERATORS.keys()))
    generator_func = PATTERN_GENERATORS[pattern_name]
    closes = generator_func(length=length, noise=noise, scale=scale)
    return pattern_name, closes

def inject_patterns_into_historical_data(symbol='BTCUSDT', 
                                         interval='15'
                                         ):
    

    pattern_length = 100  # длина паттерна, макс возможная

    symbol_auto = symbol + '_auto'
    
    data = data_base.fetch_historical_data(symbol, interval)
    
    if len(data) < pattern_length + 100:
        logger.error("Недостаточно данных. Паттерн не будет вставлен.")
        return

    # Скопируем все данные
    new_data = list(data)
    
    pattern_id = 0
    i = 50  # отступ от начала

    while i + pattern_length < len(data):
        
        pattern_length = random.randint(40, 100)  # случайная длина паттерна
        step = random.randint(150, 180)  # случайный шаг для вставки паттернов
        noise = random.uniform(0.001, 0.005)  # случайный шум для паттерна

        t_start = data[i][0]/1000
        t_end = data[i + pattern_length - 1][0]/1000

        # Базовое значение (open) для масштаба
        scale = data[i][1]

        # Генерация паттерна и OHLCV
        pattern_name, closes = generate_random_pattern(pattern_length, noise=noise, scale=scale)
        ohlcv_series = to_ohlcv(closes)

        # Привязка к предыдущей реальной свече
        prev_close = data[i - 1][4]
        ohlcv_series[0] = (prev_close, *ohlcv_series[0][1:])  # open = prev close

        # Перезаписываем в full_modified_data
        for j in range(pattern_length):
            t = data[i + j][0]
            open_, high, low, close, volume = ohlcv_series[j]
            new_data[i + j] = (t, open_, high, low, close, volume)

        # Добавим в разметку
        data_base.insert_pattern(symbol_auto, interval, pattern_name, t_start, t_end)
        
        # Переход назад к реальности
        transition_steps = 20
        real_after = data[i + pattern_length : i + pattern_length + transition_steps]  
        if len(real_after) == transition_steps:
            real_targets = [row[4] for row in real_after]
            last_close = ohlcv_series[-1][3]
            transition_data = smooth_transition(last_close, real_targets, transition_steps)

            for j in range(transition_steps):
                t = data[i + pattern_length + j][0]
                open_, high, low, close, volume = transition_data[j]
                new_data[i + pattern_length + j] = (t, open_, high, low, close, volume) 

        pattern_id += 1
        i += step

    # Сохраняем результат в таблицу
    data_base.save_to_new_table(symbol_auto, interval, new_data)

    # conn.close()
    logger.info(f"✅ Вставлено {pattern_id} паттернов в {symbol_auto}")


