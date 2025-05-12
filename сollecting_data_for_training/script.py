
import time
from datetime import datetime
from pybit.unified_trading import HTTP

from db_pattern_detection_app import MainDatabase
from loggings import LoggerManager

logger = LoggerManager().get_named_logger("pattern_detection_app")

class Agent():
    def __init__(self, queue=None):
        self.data_base = MainDatabase()

        self.__API_KEY = "XXXXX"
        self.__SECRET_KEY = "XXXXX"

        self.instance = HTTP(
            api_key=self.__API_KEY, 
            api_secret=self.__SECRET_KEY, 
            # testnet=True, 
            log_requests=True 
        )
        self.interval = "15"
        self.time_start = datetime.strptime("2023-01-01", "%Y-%m-%d").date()


    def historical_data(self, symbol, interval):
        """
            Загрузка исторыческих данных

            Аргумент:
                symbol: str - имя символа
        """
        
        self.interval = str(interval)
        logger.info(f"Загрузка данных для {symbol}")
        START = int(datetime.combine(self.time_start, datetime.min.time()).timestamp() * 1000)
        END = int(datetime.now().replace(microsecond=0).timestamp() * 1000)
        logger.debug(f"Время начала {START} Время конца {END} Интервал {self.interval}")
        # Определяю интервал в милисекундах
        units = {"1": 60000, "3": 180000, "5": 300000, "15": 900000, "30": 1800000, "60": 3600000, "120": 7200000, "240": 14400000, "360": 21600000, "720": 43200000, "D": 86400000, "W": 604800000, "M": 2592000000}
        
        # Для дообучения
        last_time = self.data_base.get_last_kline_time(symbol, self.interval)
        if last_time is False:
            print(f"Нет данных по {symbol, self.interval}")
        else:
            START = last_time

        def split_range(start, end, interval, limit=1000):
            """
                Разбивает временной промежуток на равные части по 1000 через оптеделенный интервал

                :start - от какой даты в мс
                :end - до какого времени в мс
                :interval - промежуток в мс 
                :limit=1000 - лимит значений в промежутке, опционально может быть задана если биржа имеет другой лимит ответа API
            """
            parts = []
            current_start = start
            end = end - interval  # Уменьшаем end на интервал, чтобы избежать выхода за пределы
            
            while current_start < end:
                current_end = min(current_start + interval * (limit), end)
                parts.append((current_start, current_end))
                current_start = current_end  # Начало следующего интервала
            
            return parts

        # Промежуток от начала до конца делим на части т.к. API биржи не дает больже 1000 значений
        try:
            for interval in split_range(START, END, units.get(str(self.interval), 0)):
                # logger.debug(f"Временной диапазон {interval} Интервал в милисекундах {units.get(str(self.interval), 0)}")
                kline = self.instance.get_kline(symbol=symbol, interval=self.interval, limit=1000, start=int(interval[0]), end=int(interval[1]))["result"]
                data = []
                for k in kline["list"]:
                    # Собераем порцию данных в список кортежей
                    data.append((symbol, self.interval, int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
                
                # logger.debug(f"Отладочная запись {data}")
                self.data_base.insert_kline(data[::-1]) # Запись данных в таблицу
            logger.info(f"Загрузка данных для {symbol} закончена")
            return True
        except Exception as e:
            logger.warning(f"Ошибка загрузки исторических данных {e}")

