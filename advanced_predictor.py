#!/usr/bin/env python3
"""
Predictor Avanzado IPC - Ensemble de Modelos
Combina ARIMA + XGBoost + LSTM + Variables Exógenas
Persistencia: Valida predicciones contra datos reales cuando INE publica
"""

import os
import json
import pickle
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedPredictor:
    """Predictor avanzado con múltiples modelos y persistencia"""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.models = {}
        self.scalers = {}
        self.calendar_data = {}
        self.data = None
        self.predicciones_log = "predicciones_log.json"

        self._load_models()
        self._load_calendar_data()
        self._load_data()
        self._load_predicciones_log()

    def _load_models(self):
        """Carga modelos entrenados desde disco"""
        for modelo in ['arima', 'xgboost', 'lstm']:
            path = os.path.join(self.models_dir, f"modelo_{modelo}.pkl")
            if os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        self.models[modelo] = pickle.load(f)
                    logger.info(f"✅ Modelo {modelo} cargado")
                except Exception as e:
                    logger.warning(f"⚠️  Error cargando {modelo}: {e}")
            else:
                logger.warning(f"⚠️  Modelo {modelo} no encontrado en {path}")

    def _load_calendar_data(self):
        """Carga datos de eventos calendarios"""
        try:
            with open('eventos_calendario.json', 'r', encoding='utf-8') as f:
                self.calendar_data = json.load(f)
        except Exception as e:
            logger.warning(f"⚠️  No se pudo cargar calendario: {e}")

    def _load_data(self):
        """Carga datos históricos"""
        try:
            with open('datos_bcch.json', 'r', encoding='utf-8') as f:
                bcch = json.load(f)
            historico = bcch.get('datos_historicos', [])
            self.data = pd.DataFrame(historico)
        except Exception as e:
            logger.warning(f"⚠️  Error cargando datos: {e}")

    def _load_predicciones_log(self):
        """Carga histórico de predicciones para validación"""
        if os.path.exists(self.predicciones_log):
            try:
                with open(self.predicciones_log, 'r', encoding='utf-8') as f:
                    self.predicciones_historico = json.load(f)
            except:
                self.predicciones_historico = []
        else:
            self.predicciones_historico = []

    def _get_calendar_impact(self, target_date: str) -> float:
        """Obtiene impacto de eventos calendarios"""
        try:
            mes_num = pd.to_datetime(target_date).month
            eventos = self.calendar_data.get('eventos_mensuales', {})
            mes_nombres = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                          'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

            if mes_num <= 12 and mes_nombres[mes_num - 1] in eventos:
                return eventos[mes_nombres[mes_num - 1]].get('impacto_general', 0.0)
            return 0.0
        except:
            return 0.0

    def _get_seasonal_adjustment(self, categoria: str, mes_num: int) -> float:
        """Obtiene ajuste estacional por categoría"""
        patrones = self.calendar_data.get('patrones_estacionales_por_categoria', {})

        if categoria in patrones:
            mes_nombres = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                          'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            mes_nombre = mes_nombres[mes_num - 1] if mes_num <= 12 else None

            if mes_nombre and mes_nombre in patrones[categoria]:
                return patrones[categoria][mes_nombre]
        return 0.0

    def predict_arima(self) -> Optional[float]:
        """Predicción ARIMA"""
        if 'arima' not in self.models or self.data is None:
            return None

        try:
            results = self.models['arima']
            forecast = results.get_forecast(steps=1)
            return float(forecast.predicted_mean.iloc[0])
        except Exception as e:
            logger.warning(f"⚠️  Error prediciendo ARIMA: {e}")
            return None

    def predict_xgboost(self) -> Optional[float]:
        """Predicción XGBoost con variables exógenas"""
        if 'xgboost' not in self.models or self.data is None:
            return None

        try:
            series = self.data['variacion_mensual'].values
            i = len(series) - 1

            # Features
            lag1 = series[i] if i >= 0 else 0
            lag3 = series[i-2] if i >= 2 else 0
            lag6 = series[i-5] if i >= 5 else 0
            lag12 = series[i-11] if i >= 11 else 0
            trend = np.mean(series[max(0, i-5):i+1])

            # Calendar impact
            mes_actual = self.data.iloc[-1]['mes']
            fecha_proxima = pd.to_datetime(mes_actual) + pd.DateOffset(months=1)
            calendar_impact = self._get_calendar_impact(fecha_proxima.strftime("%Y-%m"))

            X = np.array([[lag1, lag3, lag6, lag12, trend, calendar_impact]])
            prediction = self.models['xgboost'].predict(X)[0]

            return float(prediction)
        except Exception as e:
            logger.warning(f"⚠️  Error prediciendo XGBoost: {e}")
            return None

    def predict_lstm(self) -> Optional[float]:
        """Predicción LSTM"""
        if 'lstm' not in self.models or self.data is None:
            return None

        try:
            # Importar solo si es necesario
            try:
                from sklearn.preprocessing import MinMaxScaler
            except:
                return None

            scaler = MinMaxScaler()
            series_scaled = scaler.fit_transform(self.data[['variacion_mensual']])

            # Últimos 12 valores
            lookback = 12
            X = series_scaled[-lookback:].reshape(1, lookback, 1)

            prediction_scaled = self.models['lstm'].predict(X, verbose=0)[0][0]
            prediction = scaler.inverse_transform([[prediction_scaled]])[0][0]

            return float(prediction)
        except Exception as e:
            logger.warning(f"⚠️  Error prediciendo LSTM: {e}")
            return None

    def predict_ensemble(self, weights: Dict[str, float] = None) -> Dict[str, any]:
        """Predicción ensemble (promedio ponderado de modelos)"""
        if weights is None:
            weights = {'arima': 0.40, 'xgboost': 0.40, 'lstm': 0.20}

        logger.info("🔮 Generando predicción ensemble...")

        predicciones = {
            'arima': self.predict_arima(),
            'xgboost': self.predict_xgboost(),
            'lstm': self.predict_lstm(),
        }

        # Combinar predicciones disponibles
        predicciones_validas = {k: v for k, v in predicciones.items() if v is not None}

        if not predicciones_validas:
            logger.error("❌ No hay predicciones disponibles")
            return {}

        # Normalizar pesos
        pesos_normalizados = {}
        peso_total = sum(weights.get(k, 0) for k in predicciones_validas.keys())

        for k in predicciones_validas.keys():
            pesos_normalizados[k] = weights.get(k, 0) / peso_total if peso_total > 0 else 1 / len(
                predicciones_validas)

        # Ensemble
        ensemble_pred = sum(predicciones_validas[k] * pesos_normalizados[k] for k in predicciones_validas)

        resultado = {
            "timestamp": datetime.now().isoformat(),
            "predicciones_por_modelo": predicciones,
            "predicciones_validas": list(predicciones_validas.keys()),
            "pesos": pesos_normalizados,
            "ensemble_prediccion": round(ensemble_pred, 2),
            "confianza": len(predicciones_validas) / 3.0  # Confianza basada en cuántos modelos disponibles
        }

        logger.info(f"✅ Predicción ensemble: {ensemble_pred:.2f}%")
        logger.info(f"   ARIMA: {predicciones.get('arima')}")
        logger.info(f"   XGBoost: {predicciones.get('xgboost')}")
        logger.info(f"   LSTM: {predicciones.get('lstm')}")

        return resultado

    def validate_and_log(self, prediccion_fecha: str, prediccion_valor: float, valor_real: Optional[float] = None):
        """Registra predicción y valida contra valor real si está disponible"""
        try:
            entrada = {
                "fecha_prediccion": datetime.now().isoformat(),
                "prediccion_para": prediccion_fecha,
                "prediccion_valor": prediccion_valor,
                "valor_real": valor_real,
                "error": abs(prediccion_valor - valor_real) if valor_real else None
            }

            self.predicciones_historico.append(entrada)

            # Guardar
            with open(self.predicciones_log, 'w', encoding='utf-8') as f:
                json.dump(self.predicciones_historico, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Predicción registrada para {prediccion_fecha}")

            if valor_real:
                error_pct = abs(prediccion_valor - valor_real) / abs(valor_real) * 100 if valor_real != 0 else 0
                logger.info(f"   Error: {error_pct:.2f}%")

        except Exception as e:
            logger.warning(f"⚠️  Error guardando predicción: {e}")

    def get_model_performance(self) -> Dict:
        """Calcula performance de modelos histórico"""
        if not self.predicciones_historico:
            return {}

        # Filtrar predicciones con valor real
        con_real = [p for p in self.predicciones_historico if p.get('valor_real')]

        if not con_real:
            return {}

        errors = [abs(p['error']) for p in con_real if p.get('error')]

        return {
            "predicciones_totales": len(self.predicciones_historico),
            "predicciones_validadas": len(con_real),
            "mae": np.mean(errors) if errors else None,
            "rmse": np.sqrt(np.mean([e**2 for e in errors])) if errors else None,
            "acierto_direccion": sum(1 for p in con_real if np.sign(p['error']) == np.sign(p['prediccion_valor'])) / len(con_real) if con_real else None
        }


if __name__ == "__main__":
    # Test
    predictor = AdvancedPredictor()

    # Hacer predicción ensemble
    resultado = predictor.predict_ensemble()
    print(json.dumps(resultado, indent=2))

    # Mostrar performance
    perf = predictor.get_model_performance()
    print("\n📊 Performance:")
    print(json.dumps(perf, indent=2))
