import os, json
import sqlite3

from loggings import LoggerManager


logger = LoggerManager().get_named_logger("pattern_detection_app")

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
