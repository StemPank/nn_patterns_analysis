

import os
# Отключает сильно оптимизированные для вычислений на CPU, особенно на процессорах Intel
# os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import numpy as np
import random
from collections import defaultdict
from sklearn.model_selection import train_test_split
import tensorflow as tf
from keras import models
from keras import layers
# from tensorflow.keras import layers, models

from db_pattern_detection_app import MainDatabase
from loggings import LoggerManager

data_base = MainDatabase()
"""
Модель для определения паттерна на графике
"""
class PatternRecognizer:
    def __init__(self, interval: str, label_map=None):
        """
            .prepare_dataset(dataset) - для нормализации данных
            .train_model() - для обучения модели
            .predict(raw_window) - для предсказания паттерна по окну свечей
            .save_model("models/triangle_model.keras") - для сохранения модели
            .load_model("models/triangle_model.keras") - для загрузки модели
        """
        self.interval = interval
        self.label_map = label_map or {
            'ascending_triangle': 0,
            'descending_triangle': 1,
            'symmetric_triangle': 2,
            'ascending_wedge': 3,
            'descending_wedge': 4, 
            'bull_flag': 5,  
            'bear_flag': 6,  
            'none': 7,   

        }
        self.X = []
        self.y = []
        self.model = None

    def normalize_window(self, window):
        """Нормализация свечей в окне относительно первого close"""
        base_close = window[0][4]  # close первой свечи
        result = []
        for o, h, l, c, v in [(row[1], row[2], row[3], row[4], row[5]) for row in window]:
            result.append([
                (o / base_close) - 1,
                (h / base_close) - 1,
                (l / base_close) - 1,
                (c / base_close) - 1,
                v / 1000  # масштабировать объём
            ])
        return result
    
    def prepare_dataset(self, dataset=None):
        """
        Преобразовать датасет свечей (dict с названиями паттернов)
        в X (numpy массивы) и y (метки классов)
        """
        dataset = data_base.get_for_dataset(self.interval, "manual")

        for label, samples in dataset.items():
            for window in samples:
                if len(window) < 30:
                    continue
                norm = self.normalize_window(window)
                self.X.append(norm)
                self.y.append(self.label_map[label])
        self.X = np.array(self.X)
        self.y = np.array(self.y)

    def train_model(self, test_size=0.2, epochs=10):
        """
        Обучить 1D CNN на основе self.X и self.y
        """
        X_train, X_test, y_train, y_test = train_test_split(
            self.X, self.y, test_size=test_size, stratify=self.y
        )

        self.model = models.Sequential([
            layers.Input(shape=(self.X.shape[1], self.X.shape[2])),  # (window_size, 5)

            layers.Conv1D(64, kernel_size=3, activation='relu'),      # ищет шаблоны длиной 3 свечи
            layers.MaxPooling1D(2),                                   # уменьшает размер в 2 раза

            layers.Conv1D(128, kernel_size=3, activation='relu'),     # ещё один слой с фильтрами
            layers.GlobalMaxPooling1D(),                              # итоговая свёртка всех фичей

            layers.Dense(64, activation='relu'),                      # полносвязный слой
            layers.Dense(len(self.label_map), activation='softmax')        # выход — вероятности классов
        ])

        self.model.compile(optimizer='adam',
                           loss='sparse_categorical_crossentropy',
                           metrics=['accuracy'])

        self.model.fit(X_train, y_train, epochs=epochs, validation_data=(X_test, y_test))

    def predict(self, raw_window):
        """
        Предсказать класс окна свечей (дообработка и нормализация внутри)
        """
        norm = np.array([self.normalize_window(raw_window)])
        pred = self.model.predict(norm) # вероятности классов
        pred_label = np.argmax(pred) # индекс максимального значения в массиве pred (вероятностей классов)
        return pred_label, pred[0]
    
    def predict_verbose(self, raw_window):
        """
        Предсказать класс окна свечей (дообработка и нормализация внутри)
        """
        norm = np.array([self.normalize_window(raw_window)])
        pred = self.model.predict(norm)[0]  # массив вероятностей
        sorted_labels = sorted(self.label_map.items(), key=lambda x: x[1])  # гарантируем порядок
        results = [(name, round(pred[i], 4)) for name, i in sorted_labels]
        return sorted(results, key=lambda x: x[1], reverse=True)  # отсортировано по вероятности

    def save_model(self, path):
        if self.model:
            self.model.save(path)

    def load_model(self, path):
        self.model = models.load_model(path)

