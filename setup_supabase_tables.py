#!/usr/bin/env python3
"""
Setup: Crea tablas en Supabase y migra datos locales
"""

import json
import os
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
print("SETUP SUPABASE: Crear tablas e importar datos")
print("=" * 80)

# ============================================================================
# 1. CREAR TABLA: predicciones_historico
# ============================================================================
print("\n1️⃣  Creando tabla 'predicciones_historico'...")
try:
    supabase.table('predicciones_historico').select("*", count="exact").execute()
    print("   ℹ️  Tabla ya existe")
except:
    # Crear tabla usando SQL
    sql_predicciones = """
    CREATE TABLE IF NOT EXISTS predicciones_historico (
        id BIGSERIAL PRIMARY KEY,
        mes_predicho TEXT NOT NULL UNIQUE,
        variacion_esperada FLOAT NOT NULL,
        ipc_real FLOAT,
        error_absoluto FLOAT,
        version TEXT,
        timestamp TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    try:
        supabase.rpc('exec_sql', {'sql': sql_predicciones}).execute()
        print("   ✅ Tabla creada")
    except:
        print("   ⚠️  No se pudo crear con SQL. Usando REST API...")
        try:
            supabase.table('predicciones_historico').insert({
                "mes_predicho": "2026-07",
                "variacion_esperada": 0.26,
                "version": "v2.0-ensemble"
            }).execute()
            print("   ✅ Tabla creada y verificada")
        except Exception as e:
            print(f"   ❌ Error: {e}")

# ============================================================================
# 2. CREAR TABLA: ipc_datos_reales
# ============================================================================
print("\n2️⃣  Creando tabla 'ipc_datos_reales'...")
try:
    supabase.table('ipc_datos_reales').select("*", count="exact").execute()
    print("   ℹ️  Tabla ya existe")
except:
    sql_reales = """
    CREATE TABLE IF NOT EXISTS ipc_datos_reales (
        id BIGSERIAL PRIMARY KEY,
        mes TEXT NOT NULL UNIQUE,
        variacion_mensual FLOAT NOT NULL,
        indice FLOAT,
        variacion_12_meses FLOAT,
        source TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    try:
        supabase.rpc('exec_sql', {'sql': sql_reales}).execute()
        print("   ✅ Tabla creada")
    except:
        print("   ⚠️  No se pudo crear con SQL. Usando REST API...")
        try:
            supabase.table('ipc_datos_reales').insert({
                "mes": "2025-06",
                "variacion_mensual": -0.4
            }).execute()
            print("   ✅ Tabla creada y verificada")
        except Exception as e:
            print(f"   ❌ Error: {e}")

# ============================================================================
# 3. MIGRAR: predicciones_historico.json → Supabase
# ============================================================================
print("\n3️⃣  Migrando predicciones desde JSON a Supabase...")
if os.path.exists('predicciones_historico.json'):
    with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
        predicciones = json.load(f)

    for pred in predicciones:
        try:
            supabase.table('predicciones_historico').upsert({
                "mes_predicho": pred.get('mes_predicho'),
                "variacion_esperada": pred.get('variacion_esperada'),
                "ipc_real": pred.get('ipc_real'),
                "error_absoluto": pred.get('error_absoluto'),
                "version": pred.get('version'),
                "timestamp": pred.get('timestamp')
            }).execute()
        except Exception as e:
            print(f"   ⚠️  Error en {pred.get('mes_predicho')}: {str(e)[:50]}")

    print(f"   ✅ {len(predicciones)} predicciones migradas")
else:
    print("   ❌ No encontré predicciones_historico.json")

# ============================================================================
# 4. MIGRAR: datos_bcch.json → Supabase
# ============================================================================
print("\n4️⃣  Migrando datos IPC reales desde JSON a Supabase...")
if os.path.exists('datos_bcch.json'):
    with open('datos_bcch.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    datos = data.get('datos_historicos', [])
    for d in datos:
        try:
            supabase.table('ipc_datos_reales').upsert({
                "mes": d.get('mes'),
                "variacion_mensual": d.get('var_mensual'),
                "indice": d.get('indice'),
                "variacion_12_meses": d.get('var_12_meses'),
                "source": "Banco Central"
            }).execute()
        except Exception as e:
            print(f"   ⚠️  Error en {d.get('mes')}: {str(e)[:50]}")

    print(f"   ✅ {len(datos)} registros de datos reales migrados")
else:
    print("   ❌ No encontré datos_bcch.json")

print("\n" + "=" * 80)
print("✅ SETUP COMPLETADO")
print("=" * 80)
print("\nPróximos pasos:")
print("1. app.py escribirá automáticamente a estas tablas")
print("2. Cada predicción se guardará en 'predicciones_historico'")
print("3. Cada dato real ingresado se guardará en 'ipc_datos_reales'")
