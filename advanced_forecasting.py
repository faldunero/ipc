#!/usr/bin/env python3
"""
Advanced Forecasting con variables exógenas:
- ARIMA con variables exógenas (ARIMAX)
- XGBoost con features exógenas
- LSTM con inputs multivariados
- Detección de cambios de régimen
- Intervalos de confianza
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from statsmodels.tsa.arima.model import ARIMA
    from sklearn.preprocessing import StandardScaler
    import xgboost as xgb
except ImportError as e:
    logger.warning(f"⚠️ Falta librería: {e}")

# ============================================================================
# CLASE: FORECAST AVANZADO CON VARIABLES EXÓGENAS
# ============================================================================

class AdvancedForecaster:
    """Forecasting forward-looking con variables exógenas"""

    def __init__(self):
        self.datos_exogenos = self.cargar_datos_exogenos()
        self.scaler_exogenos = StandardScaler()
        logger.info("✅ AdvancedForecaster inicializado")

    def cargar_datos_exogenos(self):
        """Carga datos exógenos desde archivo"""
        try:
            with open('datos_exogenos.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("⚠️ datos_exogenos.json no encontrado. Usando valores por defecto.")
            return {
                'banco_central': {'USD': {'valor': 800}},
                'combustibles_chile': {'bencina_95': {'valor': 1150}}
            }

    def detectar_cambio_regimen(self, historico_ipc):
        """Detecta si los patrones históricos cambiaron"""
        if len(historico_ipc) < 6:
            return False, "Datos insuficientes"

        # Comparar volatilidad últimos 3 meses vs promedio histórico
        volatilidad_reciente = np.std(historico_ipc[-3:])
        volatilidad_historica = np.std(historico_ipc[:-3]) if len(historico_ipc) > 3 else volatilidad_reciente

        cambio_significativo = volatilidad_reciente > volatilidad_historica * 1.5

        return cambio_significativo, f"Vol reciente: {volatilidad_reciente:.3f} vs histórica: {volatilidad_historica:.3f}"

    def calcular_intervalo_confianza(self, prediccion, error_historico, confianza=0.95):
        """Calcula intervalo de confianza basado en error histórico"""
        # 68% confianza = 1 sigma, 95% = 1.96 sigma
        sigma = 1.96 if confianza == 0.95 else 1.0
        margen = sigma * error_historico

        return {
            'prediccion': prediccion,
            'minimo': prediccion - margen,
            'maximo': prediccion + margen,
            'margen_error': margen,
            'confianza': f"{confianza*100:.0f}%"
        }

    def forecast_arimax(self, historico_ipc, exogenas, periodos=1):
        """
        ARIMAX: ARIMA con variables exógenas
        Ejemplo: TC afecta inflación de importables
        """
        try:
            logger.info("🔮 Entrenando ARIMAX...")

            # Features exógenas normalizadas
            X_exogenas = np.array([
                exogenas.get('banco_central', {}).get('USD', {}).get('valor', 800),
                exogenas.get('combustibles_chile', {}).get('bencina_95', {}).get('valor', 1150)
            ]).reshape(1, -1)

            X_scaled = self.scaler_exogenos.fit_transform(X_exogenas)

            # Crear DataFrame con historia
            df = pd.DataFrame({
                'ipc': historico_ipc,
                'tc': np.full(len(historico_ipc), X_scaled[0, 0]),  # TC normalizado
                'combustible': np.full(len(historico_ipc), X_scaled[0, 1])
            })

            # Entrenar ARIMAX (ARIMA con exógenas)
            model = ARIMA(
                df['ipc'],
                exog=df[['tc', 'combustible']],
                order=(1, 0, 1)  # (p,d,q)
            )
            fitted = model.fit()

            # Predicción
            forecast_exog = X_scaled  # Variables futuras
            pred = fitted.get_forecast(steps=periodos, exog=forecast_exog)
            valor_predicho = pred.predicted_mean.values[0]

            logger.info(f"✅ ARIMAX predicción: {valor_predicho:.4f}%")
            return valor_predicho

        except Exception as e:
            logger.warning(f"⚠️ Error en ARIMAX: {e}")
            return np.mean(historico_ipc[-3:])  # Fallback: promedio reciente

    def forecast_xgboost_exogenas(self, historico_ipc, exogenas, periodos=1):
        """XGBoost con features exógenas + lag features"""
        try:
            logger.info("🔮 Entrenando XGBoost con exógenas...")

            # Features
            X = []
            y = []

            for i in range(3, len(historico_ipc)):
                lag1 = historico_ipc[i-1]
                lag2 = historico_ipc[i-2]
                lag3 = historico_ipc[i-3]
                tc = exogenas.get('banco_central', {}).get('USD', {}).get('valor', 800)
                combustible = exogenas.get('combustibles_chile', {}).get('bencina_95', {}).get('valor', 1150)

                X.append([lag1, lag2, lag3, tc, combustible])
                y.append(historico_ipc[i])

            if len(X) < 2:
                return np.mean(historico_ipc[-3:])

            X = np.array(X)
            y = np.array(y)

            # Entrenar
            model = xgb.XGBRegressor(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=3,
                random_state=42
            )
            model.fit(X, y, verbose=False)

            # Predicción (usar últimos valores)
            X_pred = np.array([[
                historico_ipc[-1],
                historico_ipc[-2],
                historico_ipc[-3],
                exogenas.get('banco_central', {}).get('USD', {}).get('valor', 800),
                exogenas.get('combustibles_chile', {}).get('bencina_95', {}).get('valor', 1150)
            ]])

            pred = model.predict(X_pred)[0]
            logger.info(f"✅ XGBoost predicción: {pred:.4f}%")
            return pred

        except Exception as e:
            logger.warning(f"⚠️ Error en XGBoost: {e}")
            return np.mean(historico_ipc[-3:])

    def forecast_ensemble_avanzado(self, historico_ipc, exogenas, periodos=1):
        """Ensemble que considera cambios de régimen"""

        # Detectar cambios
        cambio, razon = self.detectar_cambio_regimen(historico_ipc)

        if cambio:
            logger.warning(f"⚠️ CAMBIO DE RÉGIMEN DETECTADO: {razon}")
            # Reducir confianza si hay cambio de régimen
            peso_arimax = 0.30
            peso_xgb = 0.50
            peso_trend = 0.20
        else:
            # Pesos normales
            peso_arimax = 0.40
            peso_xgb = 0.40
            peso_trend = 0.20

        # Predicciones individuales
        pred_arimax = self.forecast_arimax(historico_ipc, exogenas, periodos)
        pred_xgb = self.forecast_xgboost_exogenas(historico_ipc, exogenas, periodos)

        # Trend simple (extrapolación)
        trend = np.mean(np.diff(historico_ipc[-6:]))
        pred_trend = historico_ipc[-1] + trend

        # Ensemble ponderado
        prediccion_ensemble = (
            peso_arimax * pred_arimax +
            peso_xgb * pred_xgb +
            peso_trend * pred_trend
        )

        # Calcular error histórico
        errores = np.abs(np.diff(historico_ipc))
        mae_historico = np.mean(errores)

        # Intervalo de confianza
        intervalo = self.calcular_intervalo_confianza(
            prediccion_ensemble,
            mae_historico,
            confianza=0.95
        )

        resultado = {
            'mes_predicho': (datetime.now() + timedelta(days=30)).strftime('%Y-%m'),
            'prediccion_ensemble': float(round(prediccion_ensemble, 4)),
            'intervalo_confianza_95': {
                'minimo': float(round(intervalo['minimo'], 4)),
                'maximo': float(round(intervalo['maximo'], 4)),
                'rango': float(round(intervalo['maximo'] - intervalo['minimo'], 4))
            },
            'cambio_regimen_detectado': bool(cambio),
            'razon_cambio': str(razon),
            'modelos_individuales': {
                'arimax': float(round(pred_arimax, 4)),
                'xgboost': float(round(pred_xgb, 4)),
                'trend': float(round(pred_trend, 4))
            },
            'pesos_ajustados': {
                'arimax': float(peso_arimax),
                'xgboost': float(peso_xgb),
                'trend': float(peso_trend)
            },
            'error_historico_mae': float(round(mae_historico, 4)),
            'timestamp': datetime.now().isoformat()
        }

        return resultado

# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    # Datos de prueba
    historico_ipc = [4.99, 4.78, 4.89, 4.59, 4.49, 4.17, 4.38, 4.07, 4.38, 3.36, 3.46, 3.46, 2.75]
    exogenas = {
        'banco_central': {'USD': {'valor': 800}},
        'combustibles_chile': {'bencina_95': {'valor': 1150}}
    }

    forecaster = AdvancedForecaster()
    resultado = forecaster.forecast_ensemble_avanzado(historico_ipc, exogenas)

    print("\n" + "="*60)
    print("📊 FORECAST AVANZADO PARA PRÓXIMO MES")
    print("="*60)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
