#!/usr/bin/env python3
"""
Integra datos reales de IPC del Banco Central a predicciones_historico
Extrae de datos_bcch.json e inserta en predicciones_historico.json y Supabase
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py no instalado")
    exit(1)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    print("❌ Falta Supabase config")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

print("=" * 80)
print("INTEGRACIÓN DE DATOS REALES DE IPC")
print("=" * 80)

# PASO 1: Leer datos reales del Banco Central
print("\n1️⃣  Leyendo datos reales de datos_bcch.json...")
with open('datos_bcch.json', 'r', encoding='utf-8') as f:
    bcch = json.load(f)

datos_reales = {d['mes']: d for d in bcch['datos_historicos']}
print(f"   ✅ {len(datos_reales)} registros de IPC reales")

# PASO 2: Leer predicciones actuales
print("\n2️⃣  Leyendo predicciones_historico.json...")
with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
    predicciones = json.load(f)

print(f"   ✅ {len(predicciones)} predicciones actuales")

# PASO 3: Actualizar con datos reales
print("\n3️⃣  Actualizando predicciones con datos reales...")
actualizadas = 0

for pred in predicciones:
    mes = pred.get('mes_predicho')
    if mes in datos_reales:
        dato_real = datos_reales[mes]
        ipc_real = float(dato_real.get('var_mensual', 0))

        if pred.get('ipc_real') != ipc_real:
            error = abs(pred.get('variacion_esperada', 0) - ipc_real)
            pred['ipc_real'] = ipc_real
            pred['error_absoluto'] = error
            actualizadas += 1
            print(f"   ✅ {mes}: {ipc_real:+.2f}% (error: {error:.2f}pp)")

# PASO 4: Guardar JSON actualizado
print("\n4️⃣  Guardando predicciones_historico.json...")
with open('predicciones_historico.json', 'w', encoding='utf-8') as f:
    json.dump(predicciones, f, indent=2, ensure_ascii=False)
print(f"   ✅ {actualizadas} predicciones actualizadas en JSON")

# PASO 5: Sincronizar a Supabase
print("\n5️⃣  Sincronizando a Supabase...")
sincronizadas = 0

for pred in predicciones:
    mes = pred.get('mes_predicho')
    try:
        supabase.table('predicciones_historico').upsert({
            "mes_predicho": mes,
            "variacion_esperada": pred.get('variacion_esperada'),
            "ipc_real": pred.get('ipc_real'),
            "error_absoluto": pred.get('error_absoluto'),
            "version": pred.get('version'),
            "timestamp": pred.get('timestamp')
        }).execute()
        sincronizadas += 1
    except Exception as e:
        print(f"   ⚠️  Error en {mes}: {str(e)[:50]}")

print(f"   ✅ {sincronizadas} predicciones sincronizadas a Supabase")

print("\n" + "=" * 80)
print("✅ INTEGRACIÓN COMPLETADA")
print("=" * 80)
print(f"\n📊 Datos reales integrados: {actualizadas}")
print(f"💾 Guardado en: predicciones_historico.json + Supabase")
print(f"\nPróximo paso: Ejecutar backtest_proper.py para validar precisión del modelo")
