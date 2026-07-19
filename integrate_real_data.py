import json
import os
from dotenv import load_dotenv

try:
    from supabase import create_client
except:
    print("❌ supabase no instalado")
    exit(1)

load_dotenv()

# Conectar Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SECRET_KEY")
)

# Leer datos reales
print("Leyendo datos reales desde Supabase...")
response = supabase.table('ipc_datos').select("mes,var_mensual").execute()
datos_reales = {d['mes']: d['var_mensual'] for d in response.data}

# Leer predicciones
with open('predicciones_historico.json') as f:
    predicciones = json.load(f)

# Integrar datos reales
for pred in predicciones:
    mes = pred.get('mes_predicho')
    if mes and mes in datos_reales:
        pred['ipc_real'] = datos_reales[mes]
        print(f"✅ {mes}: {datos_reales[mes]}")

# Guardar
with open('predicciones_historico.json', 'w') as f:
    json.dump(predicciones, f, indent=2, ensure_ascii=False)

print(f"\n✅ {len(predicciones)} predicciones con datos reales integrados")
