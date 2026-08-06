#!/usr/bin/env python3
"""
Ejemplo: Cómo usar el sistema de logging en scripts diarios
"""

from daily_execution_log import log_ejecucion_diaria, log_resumen_final
from fetch_external_data import consolidar_datos_exogenos
from advanced_forecasting import AdvancedForecaster
import json

def main():
    # 1. Iniciar log de ejecución
    log = log_ejecucion_diaria()

    try:
        # 2. Recolectar datos exógenos
        log.registrar_evento('info', 'Iniciando recolección de datos exógenos')
        datos_exogenos = consolidar_datos_exogenos()

        # Registrar datos recolectados
        if 'banco_central' in datos_exogenos:
            log.registrar_datos_recolectados(
                'Banco Central',
                len(datos_exogenos['banco_central']),
                datos_exogenos['banco_central']
            )

        if 'combustibles_chile' in datos_exogenos:
            log.registrar_datos_recolectados(
                'bencinaenlinea.cl',
                len(datos_exogenos['combustibles_chile']),
                datos_exogenos['combustibles_chile']
            )

        # 3. Entrenar modelos
        log.registrar_evento('info', 'Iniciando entrenamiento de modelos')

        # Simular entrenamiento
        log.registrar_modelo_entrenado('ARIMA', {
            'mae': 0.3552,
            'rmse': 0.4869,
            'aciertos_direccion': '54%'
        })

        log.registrar_modelo_entrenado('XGBoost', {
            'mae': 0.3200,
            'rmse': 0.4500,
            'aciertos_direccion': '58%'
        })

        log.registrar_modelo_entrenado('LSTM', {
            'mae': 0.3800,
            'rmse': 0.5100,
            'aciertos_direccion': '50%'
        })

        # 4. Generar predicción
        log.registrar_evento('info', 'Generando forecast avanzado')

        forecaster = AdvancedForecaster()
        historico_ipc = [4.99, 4.78, 4.89, 4.59, 4.49, 4.17, 4.38, 4.07, 4.38, 3.36, 3.46, 3.46, 2.75]

        resultado = forecaster.forecast_ensemble_avanzado(historico_ipc, datos_exogenos)

        log.registrar_prediccion(
            resultado['mes_predicho'],
            resultado['prediccion_ensemble'],
            resultado['intervalo_confianza_95']
        )

        # Agregar estadísticas
        log.agregar_estadistica('mae_promedio', 0.3518)
        log.agregar_estadistica('cambio_regimen', resultado.get('cambio_regimen_detectado', False))

        # 5. Generar resumen final
        log_resumen_final(log)

        print("\n✅ Ejecución completada exitosamente")
        print(f"   Logs guardados en: logs/ejecucion_*.json")

    except Exception as e:
        log.registrar_error('main', str(e))
        log_resumen_final(log)
        print(f"\n❌ Error durante ejecución: {e}")
        raise

if __name__ == '__main__':
    main()
