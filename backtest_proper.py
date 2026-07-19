#!/usr/bin/env python3
"""
Backtest Proper: Reentrenamiento mes a mes sin ver el futuro
Para cada mes objetivo (jun2025-jun2026):
1. Usar datos SOLO hasta mes anterior
2. Entrenar ARIMA + XGBoost + LSTM
3. Hacer predicción del mes siguiente
4. Comparar con dato real publicado por INE
"""

import json
import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime
from typing import Dict

# Imports para entrenamiento
try:
    from statsmodels.tsa.arima.model import ARIMA
except:
    ARIMA = None

try:
    import xgboost as xgb
except:
    xgb = None

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
except:
    LSTM = None


class BacktestModelTrainer:
    """Entrena modelos con datos históricos cutoff (sin ver el futuro)"""

    def __init__(self, data_path='datos_bcch.json'):
        with open(data_path, 'r', encoding='utf-8') as f:
            bcch = json.load(f)

        df = pd.DataFrame(bcch['datos_historicos'])
        df = df.rename(columns={
            'var_mensual': 'variacion_mensual',
            'var_12_meses': 'variacion_12_meses',
            'indice': 'ipc_index'
        })
        self.full_data = df.sort_values('mes')

    def get_data_until(self, cutoff_mes: str) -> pd.DataFrame:
        """Retorna datos HASTA un mes específico (sin incluir)"""
        return self.full_data[self.full_data['mes'] < cutoff_mes].copy()

    def train_arima(self, series):
        """Entrena ARIMA(1,1,1)"""
        if len(series) < 12:
            return None
        if ARIMA is None:
            return None
        try:
            model = ARIMA(series, order=(1, 1, 1))
            results = model.fit()
            return results
        except Exception as e:
            print(f"      [DEBUG ARIMA] Error: {str(e)[:50]}")
            return None

    def train_xgboost(self, data):
        """Entrena XGBoost con lag features"""
        if len(data) < 12:
            return None
        if xgb is None:
            return None
        try:
            series = data['variacion_mensual'].values

            # Features: lags + trend
            X, y = [], []
            for i in range(12, len(series)):
                lag1 = series[i-1]
                lag3 = series[i-3] if i >= 3 else 0
                lag6 = series[i-6] if i >= 6 else 0
                lag12 = series[i-12]
                trend = np.mean(series[max(0, i-5):i])

                X.append([lag1, lag3, lag6, lag12, trend])
                y.append(series[i])

            if len(X) < 5:
                return None

            X = np.array(X)
            y = np.array(y)

            model = xgb.XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1, verbosity=0)
            model.fit(X, y, verbose=False)
            return model
        except Exception as e:
            print(f"      [DEBUG XGB] Error: {str(e)[:50]}")
            return None

    def train_lstm(self, series):
        """Entrena LSTM simple"""
        if len(series) < 20:
            return None
        if LSTM is None or Sequential is None:
            return None
        try:
            from sklearn.preprocessing import MinMaxScaler

            scaler = MinMaxScaler()
            series_scaled = scaler.fit_transform(series.reshape(-1, 1))

            # Preparar datos
            lookback = 12
            X, y = [], []
            for i in range(lookback, len(series_scaled)):
                X.append(series_scaled[i-lookback:i, 0])
                y.append(series_scaled[i, 0])

            if len(X) < 5:
                return None

            X = np.array(X).reshape(len(X), lookback, 1)
            y = np.array(y)

            model = Sequential([
                LSTM(32, activation='relu', input_shape=(lookback, 1)),
                Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse')
            model.fit(X, y, epochs=20, batch_size=4, verbose=False)

            return (model, scaler)
        except Exception as e:
            print(f"      [DEBUG LSTM] Error: {str(e)[:50]}")
            return None

    def predict_arima(self, arima_model):
        """Predice con ARIMA"""
        try:
            return float(arima_model.get_forecast(steps=1).predicted_mean[0])
        except:
            return None

    def predict_xgboost(self, xgb_model, series):
        """Predice con XGBoost"""
        if xgb_model is None or len(series) < 12:
            return None
        try:
            lag1 = series[-1]
            lag3 = series[-3] if len(series) >= 3 else 0
            lag6 = series[-6] if len(series) >= 6 else 0
            lag12 = series[-12]
            trend = np.mean(series[-5:])

            X = np.array([[lag1, lag3, lag6, lag12, trend]])
            return float(xgb_model.predict(X)[0])
        except:
            return None

    def predict_lstm(self, lstm_data, series):
        """Predice con LSTM"""
        if lstm_data is None:
            return None
        try:
            model, scaler = lstm_data
            lookback = 12
            if len(series) < lookback:
                return None

            series_scaled = scaler.transform(series.reshape(-1, 1))
            X = series_scaled[-lookback:].reshape(1, lookback, 1)

            pred_scaled = model.predict(X, verbose=0)[0, 0]
            return float(scaler.inverse_transform([[pred_scaled]])[0, 0])
        except:
            return None


def backtest_proper():
    """Ejecuta backtest mes a mes sin ver el futuro"""

    print("=" * 80)
    print("BACKTEST PROPER: Reentrenamiento mes a mes")
    print("=" * 80)

    trainer = BacktestModelTrainer()

    # Meses a validar (cutoff = mes anterior)
    meses_validar = [
        '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12',
        '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07'
    ]

    resultados = []

    for mes_objetivo in meses_validar:
        print(f"\n{'='*80}")
        print(f"📅 Prediciendo: {mes_objetivo}")
        print(f"{'='*80}")

        # Datos HASTA mes anterior (sin incluir objetivo)
        data_cutoff = trainer.get_data_until(mes_objetivo)

        if len(data_cutoff) < 12:
            print(f"❌ Datos insuficientes ({len(data_cutoff)} registros)")
            continue

        print(f"   Datos de entrenamiento: {data_cutoff['mes'].min()} a {data_cutoff['mes'].max()}")

        # Entrenar modelos
        series = data_cutoff['variacion_mensual'].values

        arima_model = trainer.train_arima(series)
        print(f"   ARIMA: {'✅' if arima_model else '❌'}")

        xgb_model = trainer.train_xgboost(data_cutoff)
        print(f"   XGBoost: {'✅' if xgb_model else '❌'}")

        lstm_model = trainer.train_lstm(series)
        print(f"   LSTM: {'✅' if lstm_model else '❌'}")

        # Hacer predicciones
        pred_arima = trainer.predict_arima(arima_model) if arima_model else None
        pred_xgb = trainer.predict_xgboost(xgb_model, series) if xgb_model else None
        pred_lstm = trainer.predict_lstm(lstm_model, series) if lstm_model else None

        print(f"\n   Predicciones individuales:")
        print(f"   - ARIMA: {pred_arima:.2f}% " if pred_arima is not None else "   - ARIMA: N/A")
        print(f"   - XGBoost: {pred_xgb:.2f}%" if pred_xgb is not None else "   - XGBoost: N/A")
        print(f"   - LSTM: {pred_lstm:.2f}%" if pred_lstm is not None else "   - LSTM: N/A")

        # Ensemble (promedio ponderado)
        predicciones = []
        pesos = []

        if pred_arima is not None:
            predicciones.append(pred_arima)
            pesos.append(0.40)
        if pred_xgb is not None:
            predicciones.append(pred_xgb)
            pesos.append(0.40)
        if pred_lstm is not None:
            predicciones.append(pred_lstm)
            pesos.append(0.20)

        if not predicciones:
            print(f"❌ No hay predicciones disponibles")
            continue

        # Normalizar pesos
        pesos_norm = [p / sum(pesos) for p in pesos]
        ensemble = sum(p * w for p, w in zip(predicciones, pesos_norm))

        print(f"\n   🎯 Predicción Ensemble: {ensemble:.2f}%")

        # Obtener valor real
        dato_real_row = trainer.full_data[trainer.full_data['mes'] == mes_objetivo]
        if dato_real_row.empty:
            print(f"❌ No hay dato real para {mes_objetivo}")
            continue

        valor_real = float(dato_real_row.iloc[0]['variacion_mensual'])
        error = abs(ensemble - valor_real)
        direccion_correcta = (ensemble > 0) == (valor_real > 0)

        signo_ens = '+' if ensemble > 0 else ''
        signo_real = '+' if valor_real > 0 else ''
        marca = '✅' if direccion_correcta else '❌'

        print(f"\n   📊 Resultado:")
        print(f"      Predicción: {signo_ens}{ensemble:.2f}%")
        print(f"      Real (INE): {signo_real}{valor_real:.2f}%")
        print(f"      Error:      {error:.3f}pp {marca}")

        resultados.append({
            'mes': mes_objetivo,
            'prediccion': ensemble,
            'real': valor_real,
            'error': error,
            'direccion_correcta': direccion_correcta,
            'arima': pred_arima,
            'xgboost': pred_xgb,
            'lstm': pred_lstm
        })

    # Estadísticas
    print(f"\n{'='*80}")
    print("ESTADÍSTICAS FINALES")
    print(f"{'='*80}\n")

    if resultados:
        errores = [r['error'] for r in resultados]
        aciertos = sum(1 for r in resultados if r['direccion_correcta'])

        mae = np.mean(errores)
        rmse = np.sqrt(np.mean([e**2 for e in errores]))
        pct_acierto = 100 * aciertos / len(resultados)

        print(f"Predicciones totales: {len(resultados)}")
        print(f"Error Medio Absoluto (MAE): {mae:.4f}pp")
        print(f"Error Cuadrático Medio (RMSE): {rmse:.4f}pp")
        print(f"Aciertos dirección: {aciertos}/{len(resultados)} ({pct_acierto:.0f}%)\n")

        # Guardar resultados
        with open('backtest_proper_resultados.json', 'w', encoding='utf-8') as f:
            json.dump({
                'fecha': datetime.now().isoformat(),
                'resultados': resultados,
                'stats': {
                    'total': len(resultados),
                    'mae': mae,
                    'rmse': rmse,
                    'aciertos_direccion': aciertos,
                    'pct_acierto': pct_acierto
                }
            }, f, indent=2, ensure_ascii=False)

        print(f"✅ Resultados guardados en: backtest_proper_resultados.json\n")


if __name__ == "__main__":
    backtest_proper()
