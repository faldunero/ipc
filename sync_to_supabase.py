#!/usr/bin/env python3
"""
Sincroniza datos de IPC desde datos_bcch.json a Supabase
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

# Crear cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

print("Conectando a Supabase...")
print(f"URL: {SUPABASE_URL}")

# Leer datos locales
with open('datos_bcch.json', 'r', encoding='utf-8') as f:
    bcch = json.load(f)

datos = bcch['datos_historicos']
print(f"\nCargando {len(datos)} registros desde datos_bcch.json...")

# Subir a Supabase
try:
    # Primero intentar limpiar la tabla
    print("\nLimpiando tabla ipc_datos existente...")
    supabase.table('ipc_datos').delete().neq('mes', '').execute()
except:
    print("(Tabla no existe aún, creándose automáticamente)")

# Subir datos en bloques
batch_size = 100
for i in range(0, len(datos), batch_size):
    batch = datos[i:i+batch_size]
    print(f"Subiendo registros {i+1} a {min(i+batch_size, len(datos))}...")

    try:
        response = supabase.table('ipc_datos').insert(batch).execute()
        print(f"  ✅ {len(batch)} registros insertados")
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")

print("\n✅ Sincronización completada")
print(f"Total registros: {len(datos)}")
print(f"Período: {datos[0]['mes']} a {datos[-1]['mes']}")
