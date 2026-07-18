#!/usr/bin/env python3
"""
Entrenador de Modelos Avanzados para Predicción IPC
Entrena y persiste modelos: ARIMA, XGBoost, LSTM
Versión v2.0 - Con variables exógenas calendarias
"""

import os
import json
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar statsmodels
try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False
    logger.warning("⚠️  statsmodels no instalado")

# Importar sklearn para XGBoost y normalización
try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.ensemble import GradientBoostingRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("⚠️  sklearn no instalado")

# Importar xgboost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("⚠️  xgboost no instalado")

# Importar tensorflow para LSTM
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False
    logger.warning("⚠️  tensorflow no instalado")


class AdvancedModelTrainer:
    """Entrena y gestiona modelos avanzados para predicción IPC"""

    def __init__(self, data_path: str = "datos_bcch.json", models_dir: str = "models"):
        self.data_path = data_path
        self.models_dir = models_dir
        self.data = None
        self.calendar_data = None
        self.models = {}
        self.scalers = {}
        self.metadata = {}

        # Crear directorio de modelos
        os.makedirs(models_dir, exist_ok=True)

        # Cargar datos
        self._load_data()
        self._load_calendar_data()

    def _load_data(self):
        """Carga datos históricos del Banco Central"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                bcch = json.load(f)

            # Extraer histórico - buscar en diferentes estructuras
            historico = bcch.get('datos_historicos', [])

            if not historico:
                logger.error("❌ No se encontró 'datos_historicos' en el JSON")
                self.data = None
                return

            # Crear DataFrame
            df = pd.DataFrame(historico)

            # Renombrar columnas si es necesario
            rename_map = {
                'var_mensual': 'variacion_mensual',
                'var_12_meses': 'variacion_12_meses',
                'indice': 'ipc_index'
            }
            df = df.rename(columns=rename_map)

            # Verificar que tiene las columnas necesarias
            required_cols = ['mes', 'variacion_mensual', 'variacion_12_meses', 'ipc_index']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"❌ Faltan columnas. Tiene: {df.columns.tolist()}")
                self.data = None
                return

            # Convertir a datetime
            df['fecha'] = pd.to_datetime(df['mes'])
            df = df.sort_values('fecha')

            self.data = df
            logger.info(f"✅ Datos cargados: {len(df)} registros ({df['mes'].iloc[0]} a {df['mes'].iloc[-1]})")
        except Exception as e:
            logger.error(f"❌ Error cargando datos: {e}")
            import traceback
            traceback.print_exc()
            self.data = None

    def _load_calendar_data(self):
        """Carga datos de eventos calendarios"""
        try:
            with open('eventos_calendario.json', 'r', encoding='utf-8') as f:
                self.calendar_data = json.load(f)
            logger.info("✅ Datos calendarios cargados")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo cargar calendario: {e}")
            self.calendar_data = {}

    def train_arima(self, order: Tuple = (1, 1, 1)) -> bool:
        """Entrena modelo ARIMA"""
        if not ARIMA_AVAILABLE or self.data is None:
            logger.warning("⚠️  ARIMA no disponible")
            return False

        try:
            logger.info(f"📊 Entrenando ARIMA{order}...")

            series = self.data['variacion_mensual'].values
            model = ARIMA(series, order=order)
            results = model.fit()

            # Guardar modelo
            self.models['arima'] = results
            self._save_model('arima', results)

            logger.info(f"✅ ARIMA entrenado. AIC: {results.aic:.2f}")
            return True
        except Exception as e:
            logger.error(f"❌ Error entrenando ARIMA: {e}")
            return False

    def train_xgboost(self, max_depth: int = 5, n_estimators: int = 100) -> bool:
        """Entrena modelo XGBoost con variables exógenas"""
        if not XGBOOST_AVAILABLE or self.data is None:
            logger.warning("⚠️  XGBoost no disponible")
            return False

        try:
            logger.info("📊 Entrenando XGBoost...")

            # Preparar features
            X, y = self._prepare_features_xgboost()

            if X is None or len(X) < 10:
                logger.warning("⚠️  Datos insuficientes para XGBoost")
                return False

            # Entrenar
            model = xgb.XGBRegressor(
                max_depth=max_depth,
                n_estimators=n_estimators,
                learning_rate=0.1,
                random_state=42
            )
            model.fit(X, y)

            # Guardar
            self.models['xgboost'] = model
            self._save_model('xgboost', model)

            # Feature importance
            importance = pd.DataFrame({
                'feature': ['lag1', 'lag3', 'lag6', 'lag12', 'trend', 'calendar_impact'],
                'importance': model.feature_importances_[:6] if len(model.feature_importances_) >= 6 else [0]*6
            }).sort_values('importance', ascending=False)

            logger.info(f"✅ XGBoost entrenado")
            logger.info(f"   Features importantes:\n{importance.to_string()}")
            return True
        except Exception as e:
            logger.error(f"❌ Error entrenando XGBoost: {e}")
            return False

    def _prepare_features_xgboost(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepara features para XGBoost"""
        series = self.data['variacion_mensual'].values

        X_list = []
        y_list = []

        # Lags y tendencia
        for i in range(12, len(series)):
            lag1 = series[i-1]
            lag3 = series[i-3] if i >= 3 else 0
            lag6 = series[i-6] if i >= 6 else 0
            lag12 = series[i-12] if i >= 12 else 0
            trend = np.mean(series[max(0, i-6):i])

            # Calendar impact
            calendar_impact = self._get_calendar_impact(i)

            X_list.append([lag1, lag3, lag6, lag12, trend, calendar_impact])
            y_list.append(series[i])

        return np.array(X_list), np.array(y_list)

    def _get_calendar_impact(self, index: int) -> float:
        """Obtiene impacto calendario para un mes"""
        if not self.calendar_data or index >= len(self.data):
            return 0.0

        try:
            mes = self.data.iloc[index]['mes']
            mes_num = pd.to_datetime(mes).month

            eventos = self.calendar_data.get('eventos_mensuales', {})
            mes_nombre = list(eventos.keys())[mes_num - 1] if mes_num <= 12 else None

            if mes_nombre and mes_nombre in eventos:
                return eventos[mes_nombre].get('impacto_general', 0.0)
            return 0.0
        except Exception as e:
            logger.warning(f"⚠️  Error calculando calendar impact: {e}")
            return 0.0

    def train_lstm(self, lookback: int = 12, epochs: int = 50) -> bool:
        """Entrena modelo LSTM"""
        if not LSTM_AVAILABLE or self.data is None:
            logger.warning("⚠️  LSTM no disponible")
            return False

        try:
            logger.info("📊 Entrenando LSTM...")

            # Normalizar datos
            scaler = MinMaxScaler()
            series_scaled = scaler.fit_transform(self.data[['variacion_mensual']])
            self.scalers['lstm'] = scaler

            # Preparar datos
            X_list, y_list = [], []
            for i in range(len(series_scaled) - lookback):
                X_list.append(series_scaled[i:i+lookback])
                y_list.append(series_scaled[i+lookback])

            X = np.array(X_list).reshape((len(X_list), lookback, 1))
            y = np.array(y_list)

            # Construir modelo
            model = Sequential([
                LSTM(50, activation='relu', input_shape=(lookback, 1)),
                Dense(25, activation='relu'),
                Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse')

            # Entrenar
            history = model.fit(X, y, epochs=epochs, batch_size=4, verbose=0)

            self.models['lstm'] = model
            self._save_model('lstm', model)

            final_loss = history.history['loss'][-1]
            logger.info(f"✅ LSTM entrenado. Loss final: {final_loss:.4f}")
            return True
        except Exception as e:
            logger.error(f"❌ Error entrenando LSTM: {e}")
            return False

    def _save_model(self, name: str, model):
        """Guarda modelo en disco"""
        try:
            path = os.path.join(self.models_dir, f"modelo_{name}.pkl")
            with open(path, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"💾 Modelo {name} guardado en {path}")
        except Exception as e:
            logger.error(f"❌ Error guardando modelo {name}: {e}")

    def save_metadata(self):
        """Guarda metadata de entrenamiento"""
        try:
            metadata = {
                "fecha_entrenamiento": datetime.now().isoformat(),
                "num_registros": len(self.data) if self.data is not None else 0,
                "modelos_disponibles": list(self.models.keys()),
                "versions": {
                    "arima": "ARIMA(1,1,1)",
                    "xgboost": "XGBoost con variables exógenas",
                    "lstm": "LSTM con 50 unidades"
                }
            }

            path = os.path.join(self.models_dir, "metadata.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Metadata guardada")
        except Exception as e:
            logger.error(f"❌ Error guardando metadata: {e}")

    def train_all(self) -> Dict[str, bool]:
        """Entrena todos los modelos disponibles"""
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO ENTRENAMIENTO DE TODOS LOS MODELOS")
        logger.info("=" * 60)

        results = {
            "arima": self.train_arima(),
            "xgboost": self.train_xgboost(),
            "lstm": self.train_lstm()
        }

        self.save_metadata()

        logger.info("=" * 60)
        logger.info("✅ ENTRENAMIENTO COMPLETADO")
        logger.info(f"   Modelos exitosos: {sum(results.values())}/{len(results)}")
        logger.info("=" * 60)

        return results


if __name__ == "__main__":
    # Entrenar todos los modelos
    trainer = AdvancedModelTrainer()
    trainer.train_all()
