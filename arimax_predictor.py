#!/usr/bin/env python3
"""
ARIMA Predictor - Modelo serio y predictivo
- Datos reales del Banco Central (36+ meses)
- ARIMA (AutoRegressive Integrated Moving Average)
- Walk-forward backtesting
"""

import numpy as np
import pandas as pd
import requests
import json
from datetime import datetime
import logging
from statsmodels.tsa.arima.model import ARIMA
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class ARIMAPredictor:
    """Predictor ARIMA para IPC"""

    def __init__(self):
        self.ipc_historico = []
        self.fechas = []

    def fetch_datos(self):
        """Carga datos históricos desde archivo local"""
        try:
            logger.info("📊 Cargando IPC mensual desde datos_historicos_36m.json...")

            with open('datos_historicos_36m.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                try:
                    valor = float(item.get('ipc_var_mensual', 0))
                    mes_str = item['mes']
                    fecha = datetime.strptime(mes_str + '-01', '%Y-%m-%d')

                    self.ipc_historico.append(valor)
                    self.fechas.append(fecha)
                except Exception as e:
                    logger.warning(f"⚠️ Error parseando {item.get('mes')}: {e}")

            logger.info(f"✅ {len(self.ipc_historico)} meses de IPC cargados")
            return len(self.ipc_historico) >= 12

        except Exception as e:
            logger.error(f"❌ Error cargando datos: {e}")
            return False

    def entrenar_arima_walkforward(self, order=(1, 1, 1)):
        """Entrena ARIMA con walk-forward validation"""
        logger.info("\n" + "="*70)
        logger.info("🔮 ENTRENANDO ARIMA CON WALK-FORWARD VALIDATION")
        logger.info("="*70)

        if len(self.ipc_historico) < 12:
            logger.error("❌ Datos insuficientes")
            return None

        predicciones = []
        reales = []
        errores_abs = []

        train_size = 12  # Entrenar con últimos 12 meses

        for i in range(train_size, len(self.ipc_historico)):
            try:
                train_ipc = self.ipc_historico[i-train_size:i]
                real = self.ipc_historico[i]

                modelo = ARIMA(train_ipc, order=order)
                resultado = modelo.fit()

                pred = resultado.get_forecast(steps=1)
                valor_pred = float(pred.predicted_mean[0])

                predicciones.append(valor_pred)
                reales.append(real)
                error = abs(valor_pred - real)
                errores_abs.append(error)

                logger.info(f"  Mes {i}: Predicción {valor_pred:.4f}% | Real {real:.4f}% | Error {error:.4f}%")

            except Exception as e:
                logger.warning(f"  ⚠️ Error en mes {i}: {str(e)[:50]}")
                continue

        if not predicciones:
            logger.error("❌ No se pudieron generar predicciones")
            return None

        mae = np.mean(errores_abs)
        rmse = np.sqrt(np.mean(np.array(errores_abs)**2))

        direccionales = 0
        if len(predicciones) > 1:
            for j in range(1, len(predicciones)):
                if (predicciones[j] > predicciones[j-1] and reales[j] > reales[j-1]) or \
                   (predicciones[j] <= predicciones[j-1] and reales[j] <= reales[j-1]):
                    direccionales += 1
            pct_acierto_dir = (direccionales / (len(predicciones)-1)) * 100
        else:
            pct_acierto_dir = 0

        logger.info("\n" + "="*70)
        logger.info("📊 RESULTADOS ARIMA:")
        logger.info(f"  MAE (Error Medio Absoluto): {mae:.4f}%")
        logger.info(f"  RMSE: {rmse:.4f}%")
        logger.info(f"  Aciertos Direccionales: {pct_acierto_dir:.1f}%")
        logger.info(f"  Predicciones: {len(predicciones)} meses validados")
        logger.info("="*70 + "\n")

        return {
            'mae': float(mae),
            'rmse': float(rmse),
            'aciertos_direccion': float(pct_acierto_dir),
            'predicciones': predicciones,
            'reales': reales,
            'errores': errores_abs,
            'modelo_params': order,
            'timestamp': datetime.now().isoformat()
        }

    def predecir_siguiente_mes(self, order=(1, 1, 1)):
        """Predice el siguiente mes"""
        try:
            logger.info("🔮 Prediciendo siguiente mes...")

            if len(self.ipc_historico) < 12:
                logger.error("❌ Datos insuficientes")
                return None

            modelo = ARIMA(self.ipc_historico, order=order)
            resultado = modelo.fit()

            pred = resultado.get_forecast(steps=1)
            valor_pred = float(pred.predicted_mean[0])

            conf_int = pred.conf_int(alpha=0.05)
            min_val = float(conf_int[0, 0])
            max_val = float(conf_int[0, 1])

            logger.info(f"✅ Predicción siguiente mes: {valor_pred:.4f}%")
            logger.info(f"   IC 95%: [{min_val:.4f}%, {max_val:.4f}%]")

            return {
                'prediccion': valor_pred,
                'intervalo_confianza': {
                    'min': min_val,
                    'max': max_val
                },
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Error prediciendo: {e}")
            return None

    def guardar_resultados(self, resultados):
        """Guarda resultados"""
        try:
            with open('arimax_resultados.json', 'w', encoding='utf-8') as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            logger.info("✅ Resultados guardados en arimax_resultados.json")
        except Exception as e:
            logger.error(f"❌ Error guardando: {e}")

if __name__ == '__main__':
    predictor = ARIMAPredictor()

    if not predictor.fetch_datos():
        logger.error("❌ No hay suficientes datos")
        exit(1)

    resultados_backtest = predictor.entrenar_arima_walkforward(order=(1, 1, 1))
    resultado_pred = predictor.predecir_siguiente_mes(order=(1, 1, 1))

    if resultados_backtest:
        resultados_backtest['proxima_prediccion'] = resultado_pred
        predictor.guardar_resultados(resultados_backtest)

    logger.info("✅ Proceso completado")
