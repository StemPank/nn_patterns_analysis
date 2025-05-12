import os, json
import sqlite3
import random

from loggings import LoggerManager


logger = LoggerManager().get_named_logger("data_for_pattern")

class MainDatabase():
    def __init__(self):
        self.create_table_kline()
        self.create_table_patterns()

    def get_connection(self):
        conn = sqlite3.connect("fisher_data.sqlite")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_table_kline(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS kline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,           -- например, BTCUSDT
                    interval TEXT NOT NULL,         -- '1h', '15m', '5m'
                    time INTEGER NOT NULL,          -- UNIX timestamp
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    UNIQUE(symbol, interval, time)
                );
        ''')
        
        logger.debug(f"Таблица kline создана")
        connection.commit()
        connection.close()

    def insert_kline(self, data):
        """
        data: список кортежей вида:
            [(symbol, interval, time, open, high, low, close, volume), ...]
        """
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.executemany('''
                INSERT OR IGNORE INTO kline (symbol, interval, time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
        except Exception as e:
            logger.error(f"Ошибка при вставке kline: {e}")
        
        
        connection.commit()
        connection.close()

    def save_to_new_table(self, symbol_auto, interval, data):
        """Для записи автоматически созданных результатов"""
        connection = self.get_connection()
        cursor = connection.cursor()
        for row in data:
            time, open_, high, low, close, volume = row
            cursor.execute("""
                INSERT INTO kline (symbol, interval, time, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol_auto, interval, time, open_, high, low, close, volume))
        connection.commit()
        connection.close()

    def get_klines(self, symbol, interval, start_time=None, end_time=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        query = '''
            SELECT time, open, high, low, close
            FROM kline
            WHERE symbol = ? AND interval = ?
        '''
        params = [symbol, interval]

        if start_time:
            query += ' AND time >= ?'
            params.append(start_time)
        if end_time:
            query += ' AND time <= ?'
            params.append(end_time)

        query += ' ORDER BY time ASC'

        cursor.execute(query, params)
        res = cursor.fetchall()
        connection.close()
        return res

    def fetch_historical_data(self, symbol, interval):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT time, open, high, low, close, volume
            FROM kline
            WHERE symbol = ? AND interval = ?
            ORDER BY time ASC
        """, (symbol, interval))
        res = cursor.fetchall()
        connection.close()
        return res

    def get_last_kline_time(self, symbol, interval):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('''
            SELECT MAX(time)
            FROM kline
            WHERE symbol = ? AND interval = ?
        ''', (symbol, interval))

        result = cursor.fetchone()
        last_time = result[0] if result and result[0] is not None else None
        
        res = int(last_time) if last_time is not None else False
        connection.close()
        return res




    def create_table_patterns(self):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,         -- например: triangle, h&s, double_top
                    start_time INTEGER NOT NULL,
                    end_time INTEGER NOT NULL,
                    label_by TEXT DEFAULT 'manual'      -- кто размечал: 'manual', 'auto'
                );
        ''')
        
        logger.debug(f"Таблица patterns создана")
        connection.commit()
        connection.close()
    
    def insert_pattern(self, symbol, interval, pattern_type, start_time, end_time, label_by='manual'):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO patterns (symbol, interval, pattern_type, start_time, end_time, label_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                interval,
                pattern_type,
                start_time,
                end_time,
                label_by
            ))
            connection.commit()
        except Exception as e:
            logger.error(f"Ошибка при вставке паттерна: {e}")
    
    def get_patterns(self, symbol, interval):
        connection = self.get_connection()
        cursor = connection.cursor()
        cursor.execute('''
            SELECT pattern_type, start_time, end_time
            FROM patterns
            WHERE symbol = ? AND interval = ?
            ORDER BY start_time ASC
        ''', (symbol, interval))
        res = cursor.fetchall()
        connection.close()
        return [
            {
                'pattern_type': row[0],
                'start_time': row[1],
                'end_time': row[2]
            } for row in res
        ]

    
    
    #for dataset
    def get_for_dataset(self, interval, label_by, buffer=10, stec=120): # stec - длинна паттерна для обучения, макс. длинна паттерна + buffer*2
        """Формирование датасета"""
        from collections import defaultdict

        connection = self.get_connection()
        cursor = connection.cursor()
        # запрос на получение всех паттернов
        cursor.execute('''
            SELECT symbol, interval, pattern_type, start_time, end_time, label_by
            FROM patterns;
        ''')
        patterns = cursor.fetchall()
        logger.debug(patterns[:3])
        
        dataset = defaultdict(list)
        used_ranges = []

        # Переводим интервал в милисекунды
        units = {"1": 60000, "3": 180000, "5": 300000, "15": 900000, "30": 1800000, "60": 3600000, "120": 7200000, "240": 14400000, "360": 21600000, "720": 43200000, "D": 86400000, "W": 604800000, "M": 2592000000}
        buffer_ = units.get(str(interval), 0)
        
        for p in patterns:
            symbol, interval, pattern_type = p[0], p[1], p[2]
            start_time, end_time = p[3], p[4]

            # Получаем данные по паттерну и в стороны от него на buffer
            cursor.execute(
                """
                SELECT time, open, high, low, close, volume
                FROM kline
                WHERE symbol = ? AND interval = ? AND time BETWEEN ? AND ?
                ORDER BY time
                """,
                (symbol, interval, start_time*1000 - buffer * buffer_, end_time*1000 + buffer * buffer_)
            )
            candles = cursor.fetchall()

            if len(candles) < stec: # если паттерн меньше чем stec, то добавляем еще buffer свечей перед паттерном
                # logger.debug(f"Длинна паттерна {len(candles)}")
                diff = stec - len(candles) # разница между паттерном и stec
                # logger.debug(f"Разница difference = {diff}")
                cursor.execute(
                    """
                    SELECT time, open, high, low, close, volume
                    FROM kline
                    WHERE symbol = ? AND interval = ? AND time BETWEEN ? AND ?
                    ORDER BY time
                    """,
                    (symbol, interval, start_time*1000 - (buffer + diff) * buffer_, end_time*1000 + buffer * buffer_)
                )
                candles = cursor.fetchall()
                

            # logger.debug(candles[:3])

            if len(candles) > 0:
                # logger.debug(f"длинна записаного паттерна {len(candles)}")
                dataset[pattern_type].append(candles) # добавляем паттерн в датасет
                used_ranges.append((symbol, interval, start_time*1000 - buffer * buffer_, end_time*1000 + buffer * buffer_)) # запоминаем диапазон паттерна
          
        # Получаем негативные примеры — участки без паттернов
        key_syimbol = defaultdict(list)
        for p in used_ranges: 
            # записывает время конца предыдущего паттерна и время начала текущего, в промежутке между ними ищет негативные паттерны
            symbol, interval, start_time, end_time = p[0], p[1], p[2], p[3]
            if (symbol, interval) not in key_syimbol:
                key_syimbol[(symbol, interval)] = end_time
            else:
                end_time_ = start_time
                start_time_ = key_syimbol[(symbol, interval)]
                diapason = (start_time_-end_time_)//buffer_

                if diapason > 130:  # stec + i (отступ от начала)
                
                    window_size = 100 + buffer*2 # maximum длина паттерна
                    i = 10 # отступ от начала т.к. буфер 10, чтобы не пересекаться с паттерном

                    while i + window_size < diapason:
                        window_size = random.randint(40, 100) # кол-во свечей для одного примера
                        step = random.randint(120, 140) # шаг для сдвига паттерна, чтобы не пересекаться с паттерном
                        
                        # Получаем буферизированные границы
                        cursor.execute(
                            """
                            SELECT time, open, high, low, close, volume
                            FROM kline
                            WHERE symbol = ? AND interval = ? AND time BETWEEN ? AND ?
                            ORDER BY time
                            """,
                            (symbol, interval, start_time_ + i * buffer_, start_time_ + (i + window_size) * buffer_)
                        )
                        candles = cursor.fetchall()

                        if len(candles) < stec: # если паттерн меньше чем stec, то добавляем еще buffer свечей
                            # logger.debug(f"Длинна паттерна {len(candles)}")
                            diff = stec - len(candles)
                            # logger.debug(f"Разница difference = {diff}")
                            cursor.execute(
                                """
                                SELECT time, open, high, low, close, volume
                                FROM kline
                                WHERE symbol = ? AND interval = ? AND time BETWEEN ? AND ?
                                ORDER BY time
                                """,
                                (symbol, interval, start_time_ + i * buffer_, start_time_ + (i + window_size + diff) * buffer_)
                            )
                            candles = cursor.fetchall()

                        if len(candles) > 0:
                            dataset["none"].append(candles)

                        i += step

                    key_syimbol[(symbol, interval)] = end_time

        connection.close()
        # logger.info(f"Получено {dataset['ascending_triangle'][0]}")
        logger.info(f"Получено {len(dataset['ascending_triangle'])} паттернов для ascending_triangle")
        logger.info(f"Получено {len(dataset['descending_triangle'])} паттернов для descending_triangle")
        logger.info(f"Получено {len(dataset['symmetric_triangle'])} паттернов для symmetric_triangle")
        logger.info(f"Получено {len(dataset['ascending_wedge'])} паттернов для ascending_wedge")
        logger.info(f"Получено {len(dataset['descending_wedge'])} паттернов для descending_wedge")
        logger.info(f"Получено {len(dataset['bull_flag'])} паттернов для bull_flag")
        logger.info(f"Получено {len(dataset['bear_flag'])} паттернов для bear_flag")
        logger.info(f"Получено {len(dataset['none'])} паттернов для none")
        logger.debug(dataset.keys())
        return dataset






    def delete_symbol_data(self, symbol):
        """
        Удаляет данные по символу из таблиц kline и patterns
        """
        connection = self.get_connection()
        cursor = connection.cursor()

        # Удаление из таблицы свечей
        cursor.execute("DELETE FROM kline WHERE symbol = ?", (symbol,))
        print(f"🗑 Удалено из klines: {cursor.rowcount} строк для символа {symbol}")

        # Удаление из таблицы паттернов
        cursor.execute("DELETE FROM patterns WHERE symbol = ?", (symbol,))
        print(f"🗑 Удалено из patterns: {cursor.rowcount} строк для символа {symbol}")

        connection.commit()
        connection.close()
        print("✅ Удаление завершено.")





if __name__ == "__main__":
    db = MainDatabase()
    # db.delete_symbol_data("BTCUSDT_auto")
    db.get_for_dataset(15, "manual")