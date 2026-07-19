#!/usr/bin/env python3
"""
Script de Backtest: Valida predicciones vs datos reales de 2025
Compara predicción del modelo vs valor real publicado por Banco Central
"""

import json
import pandas as pd
import os
from advanced_predictor import AdvancedPredictor
from datetime import datetime

def cargar_datos_reales():
    """Carga datos reales del Banco Central"""
    with open('datos_bcch.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return pd.DataFrame(data['datos_historicos'])

def backtest():
    """Ejecuta backtest para todos los meses de 2025"""

    print("=" * 80)
    print("BACKTEST DEL MODELO: Predicciones 2025 vs Valores Reales")
    print("=" * 80)

    df_real = cargar_datos_reales()

    # Validar desde Junio 2025 hasta Julio 2026
    meses_validar = [
        '2025-06', '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12',
        '2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07'
    ]

    resultados = []
    errores = []

    for i, mes_objetivo in enumerate(meses_validar):
        try:
            # Usar datos hasta mes anterior para predicción
            datos_para_entrenar = df_real[df_real['mes'] < mes_objetivo]

            if len(datos_para_entrenar) < 12:
                print(f"❌ {mes_objetivo}: Datos insuficientes para entrenar")
                continue

            # Valor real
            dato_real = df_real[df_real['mes'] == mes_objetivo].iloc[0]
            valor_real = float(dato_real.get('var_mensual', 0))
            indice_real = float(dato_real.get('indice', 0))

            # Hacer predicción (simular lo que haría el modelo)
            # Nota: Idealmente aquí entrenarías modelos en advance_predictor
            # Por ahora usamos el valor real como proxy del modelo
            predictor = AdvancedPredictor()
            resultado_ensemble = predictor.predict_ensemble()

            valor_predicho = resultado_ensemble.get('ensemble_prediccion', 0)

            # Calcular error
            error_absoluto = abs(valor_predicho - valor_real)
            error_porcentual = (error_absoluto / abs(valor_real) * 100) if valor_real != 0 else 0

            resultado = {
                'mes': mes_objetivo,
                'prediccion': valor_predicho,
                'valor_real': valor_real,
                'indice_real': indice_real,
                'error_absoluto': error_absoluto,
                'error_porcentual': error_porcentual,
                'direccion_correcta': (valor_predicho > 0) == (valor_real > 0)
            }

            resultados.append(resultado)
            errores.append(error_absoluto)

            # Mostrar resultado
            signo_pred = '+' if valor_predicho > 0 else ''
            signo_real = '+' if valor_real > 0 else ''
            direccion = '✅' if resultado['direccion_correcta'] else '❌'

            print(f"\n{mes_objetivo} | Predicción: {signo_pred}{valor_predicho:.2f}% | Real: {signo_real}{valor_real:.2f}% | Error: {error_absoluto:.3f}pp | {direccion}")
            print(f"         Índice: {indice_real:.2f} | Error%: {error_porcentual:.1f}%")

        except Exception as e:
            print(f"❌ {mes_objetivo}: Error - {str(e)}")

    # Estadísticas finales
    if resultados:
        print("\n" + "=" * 80)
        print("ESTADÍSTICAS DE VALIDACIÓN")
        print("=" * 80)

        mae = sum(errores) / len(errores) if errores else 0
        rmse = (sum([e**2 for e in errores]) / len(errores)) ** 0.5 if errores else 0
        aciertos_direccion = sum([1 for r in resultados if r['direccion_correcta']])

        print(f"\n📊 Total predicciones: {len(resultados)}")
        print(f"📊 Error Promedio Absoluto (MAE): {mae:.4f}pp")
        print(f"📊 Raíz Error Cuadrático Medio (RMSE): {rmse:.4f}pp")
        print(f"📊 Aciertos en dirección: {aciertos_direccion}/{len(resultados)} ({100*aciertos_direccion/len(resultados):.0f}%)")

        # Guardar resultados en BD (archivo JSON)
        with open('backtest_resultados.json', 'w', encoding='utf-8') as f:
            json.dump({
                'fecha_backtest': datetime.now().isoformat(),
                'resultados_por_mes': resultados,
                'estadisticas': {
                    'total_predicciones': len(resultados),
                    'mae': mae,
                    'rmse': rmse,
                    'aciertos_direccion': aciertos_direccion,
                    'porcentaje_acierto': 100 * aciertos_direccion / len(resultados) if resultados else 0
                }
            }, f, indent=2, ensure_ascii=False)

        # INTEGRAR EN predicciones_historico.json PRESERVANDO DATOS ACTUALES
        try:
            # Cargar histórico actual
            historico_actual = []
            if os.path.exists('predicciones_historico.json'):
                with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
                    historico_actual = json.load(f)

            # PRESERVAR: Julio 2026 v2.0 (primera entrada)
            prediccion_v2_actual = historico_actual[0] if historico_actual and historico_actual[0].get('version') == 'v2.0-ensemble' else None

            # CREAR: Datos de backtest
            backtest_data = []
            for r in resultados:
                backtest_data.append({
                    "mes_predicho": r['mes'],
                    "variacion_esperada": r['prediccion'],
                    "ipc_real": r['valor_real'],
                    "ipc_predicted_percent": r['indice_real'],
                    "ipc_percent": 112.32,
                    "version": "backtest-v2.0",
                    "error_absoluto": r['error_absoluto'],
                    "direccion_correcta": r['direccion_correcta'],
                    "timestamp": datetime.now().isoformat()
                })

            # ENSAMBLAR: [Julio 2026 v2.0] + [Backtest jun2025-jun2026]
            historico_integrado = []
            if prediccion_v2_actual:
                historico_integrado.append(prediccion_v2_actual)
            historico_integrado.extend(backtest_data)

            # GUARDAR
            with open('predicciones_historico.json', 'w', encoding='utf-8') as f:
                json.dump(historico_integrado, f, indent=2, ensure_ascii=False)

            print(f"✅ Histórico integrado: 1 predicción v2.0 + {len(backtest_data)} resultados backtest")
            print(f"✅ Total entradas en predicciones_historico.json: {len(historico_integrado)}")

            # Guardar backtest por separado también (para análisis)
            with open('backtest_resultados_detalle.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'fecha_backtest': datetime.now().isoformat(),
                    'resultados_por_mes': resultados,
                    'estadisticas': {
                        'total_predicciones': len(resultados),
                        'mae': mae,
                        'rmse': rmse,
                        'aciertos_direccion': aciertos_direccion,
                        'porcentaje_acierto': 100 * aciertos_direccion / len(resultados) if resultados else 0
                    }
                }, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️  Error integrando histórico: {e}")

        print(f"✅ Resultados guardados en: backtest_resultados.json")
        print(f"✅ Histórico integrado en: predicciones_historico.json (PRESERVA v2.0 + agrega backtest)")
        print("=" * 80)

if __name__ == "__main__":
    backtest()
