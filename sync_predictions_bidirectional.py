#!/usr/bin/env python3
"""
Sincronización bidireccional: predicciones_historico.json ↔ Supabase
Ejecutar cada 7 días a las 2 AM
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py no instalado. Ejecuta: pip install supabase")
    exit(1)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    print("❌ Falta SUPABASE_URL o SUPABASE_SECRET_KEY en .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

print("=" * 80)
print(f"SINCRONIZACIÓN BIDIRECCIONAL: {datetime.now().isoformat()}")
print("=" * 80)

# ============================================================================
# PASO 1: LEER desde JSON local
# ============================================================================
print("\n1️⃣  Leyendo predicciones desde JSON local...")
if not os.path.exists('predicciones_historico.json'):
    print("   ❌ No encontré predicciones_historico.json")
    exit(1)

with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
    predicciones_json = json.load(f)

print(f"   ✅ {len(predicciones_json)} predicciones leídas del JSON")

# ============================================================================
# PASO 2: LEER desde Supabase
# ============================================================================
print("\n2️⃣  Leyendo predicciones desde Supabase...")
try:
    response = supabase.table('predicciones_historico').select("*").execute()
    predicciones_bd = response.data if response.data else []
    print(f"   ✅ {len(predicciones_bd)} predicciones leídas de Supabase")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# ============================================================================
# PASO 3: COMPARAR y SINCRONIZAR
# ============================================================================
print("\n3️⃣  Sincronizando datos...")

# Convertir BD a diccionario por mes para fácil comparación
bd_dict = {p['mes_predicho']: p for p in predicciones_bd}
json_dict = {p['mes_predicho']: p for p in predicciones_json}

# Contadores
insertadas = 0
actualizadas = 0
eliminadas = 0

# A) Insertar/Actualizar predicciones del JSON que no están en BD o son diferentes
for mes, pred in json_dict.items():
    if mes not in bd_dict:
        # Nueva predicción
        try:
            supabase.table('predicciones_historico').insert({
                "mes_predicho": pred.get('mes_predicho'),
                "variacion_esperada": pred.get('variacion_esperada'),
                "ipc_real": pred.get('ipc_real'),
                "error_absoluto": pred.get('error_absoluto'),
                "version": pred.get('version'),
                "timestamp": pred.get('timestamp')
            }).execute()
            insertadas += 1
            print(f"   ✨ Insertada: {mes}")
        except Exception as e:
            print(f"   ⚠️  Error insertando {mes}: {str(e)[:50]}")
    else:
        # Comparar si hay cambios
        bd_pred = bd_dict[mes]
        cambios = False

        if pred.get('variacion_esperada') != bd_pred.get('variacion_esperada'):
            cambios = True
        if pred.get('ipc_real') != bd_pred.get('ipc_real'):
            cambios = True
        if pred.get('error_absoluto') != bd_pred.get('error_absoluto'):
            cambios = True

        if cambios:
            try:
                supabase.table('predicciones_historico').update({
                    "variacion_esperada": pred.get('variacion_esperada'),
                    "ipc_real": pred.get('ipc_real'),
                    "error_absoluto": pred.get('error_absoluto'),
                    "version": pred.get('version'),
                    "timestamp": pred.get('timestamp')
                }).eq('mes_predicho', mes).execute()
                actualizadas += 1
                print(f"   🔄 Actualizada: {mes}")
            except Exception as e:
                print(f"   ⚠️  Error actualizando {mes}: {str(e)[:50]}")

# B) Eliminar predicciones que están en BD pero no en JSON
for mes, pred in bd_dict.items():
    if mes not in json_dict:
        try:
            supabase.table('predicciones_historico').delete().eq('mes_predicho', mes).execute()
            eliminadas += 1
            print(f"   🗑️  Eliminada: {mes}")
        except Exception as e:
            print(f"   ⚠️  Error eliminando {mes}: {str(e)[:50]}")

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "=" * 80)
print("✅ SINCRONIZACIÓN COMPLETADA")
print("=" * 80)
print(f"\n📊 Resumen:")
print(f"   Insertadas: {insertadas}")
print(f"   Actualizadas: {actualizadas}")
print(f"   Eliminadas: {eliminadas}")
print(f"\n🔒 JSON local sigue siendo la fuente de verdad")
print(f"📅 Próxima sincronización: En 7 días a las 02:00 AM")
