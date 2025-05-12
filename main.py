from сollecting_data_for_training.script import Agent
from сollecting_data_for_training.auto_data import inject_patterns_into_historical_data
from manual_marking.app import app
from training import PatternRecognizer
from db_pattern_detection_app import MainDatabase

database = MainDatabase()

listing = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "ADAUSDT",
    "SOLUSDT"
]

# Загрузка исторических данных и инъекция авто.созданных паттернов в базу данных с кланированием табльц (_auto)
# for syimbol in listing:
#     Agent().historical_data(syimbol, 15) # Загрузка исторических данных
#     inject_patterns_into_historical_data(symbol = syimbol, interval='15')



sample_window = database.fetch_historical_data("BTCUSDT", 15) # Данные для теста

recognizer = PatternRecognizer(interval=15) # Инициализация, модель чуствительна к интервалу
recognizer.prepare_dataset() # Подготовка датасета для обучения
recognizer.train_model() # Обучение модели

i_test = len(sample_window)-120 # Индекс для теста, 120 свечей от конца (120 свечей матрица для обучения модели) 

# Предсказание:
# pred_label, confidences = recognizer.predict(sample_window[test:])
result = recognizer.predict_verbose(sample_window[i_test:]) # Предсказание с вероятностями
for label, prob in result:
    print(f"{label}: {prob * 100:.2f}%")

