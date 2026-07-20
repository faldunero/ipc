#!/usr/bin/env python3
"""API Backend para Predictor IPC - FastAPI"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ipc_predictor import IPCPredictor
from advanced_predictor import AdvancedPredictor
import os
import json
from dotenv import load_dotenv

# Intentar importar Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  supabase-py no instalado")

# Cargar .env
load_dotenv()

app = FastAPI(title="Predictor IPC")

# Inicializar Supabase si está disponible
supabase_client = None
if SUPABASE_AVAILABLE:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
    if SUPABASE_URL and SUPABASE_SECRET_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
        print(f"✅ Supabase conectado: {SUPABASE_URL}")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
predictor = None
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class PredictionResponse(BaseModel):
    prediccion_ipc: float
    variacion_esperada: float
    ipc_actual: float
    metodo_estadistico: float
    metodo_groq: float

class PredictionV2Response(BaseModel):
    ensemble_prediccion: float
    predicciones_por_modelo: dict
    pesos: dict
    confianza: float
    timestamp: str

@app.on_event("startup")
def startup():
    """Inicializar predictor al arrancar"""
    global predictor

    groq_key = GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    print(f"DEBUG: GROQ_API_KEY found: {bool(groq_key)}")

    if not groq_key:
        print("⚠️  GROQ_API_KEY no configurada. Usando modo demo")
        groq_key = "demo_key_for_data_only"

    try:
        predictor = IPCPredictor(groq_key)
        predictor.fetch_ine_data()
        print("✅ Predictor inicializado")
    except Exception as e:
        print(f"⚠️  Error: {e}")
        print("✅ Continuando con datos locales únicamente")

# ============================================================================
# FUNCIONES HELPER PARA SUPABASE
# ============================================================================

def guardar_prediccion_a_supabase(mes_predicho: str, variacion_esperada: float, version: str = "v2.0-ensemble"):
    """Guarda una predicción en Supabase"""
    if not supabase_client:
        print("⚠️  Supabase no disponible, predicción no guardada en BD")
        return False

    try:
        from datetime import datetime
        supabase_client.table('predicciones_historico').upsert({
            "mes_predicho": mes_predicho,
            "variacion_esperada": variacion_esperada,
            "version": version,
            "timestamp": datetime.now().isoformat()
        }).execute()
        print(f"✅ Predicción {mes_predicho} guardada en Supabase")
        return True
    except Exception as e:
        print(f"⚠️  Error guardando predicción en Supabase: {str(e)[:100]}")
        return False

def guardar_dato_real_a_supabase(mes: str, variacion_mensual: float, indice: float = None):
    """Guarda un dato real de IPC en Supabase"""
    if not supabase_client:
        print("⚠️  Supabase no disponible, dato no guardado en BD")
        return False

    try:
        supabase_client.table('ipc_datos_reales').upsert({
            "mes": mes,
            "variacion_mensual": variacion_mensual,
            "indice": indice,
            "source": "Manual - Usuario"
        }).execute()
        print(f"✅ Dato real {mes} guardado en Supabase")
        return True
    except Exception as e:
        print(f"⚠️  Error guardando dato real en Supabase: {str(e)[:100]}")
        return False

def actualizar_prediccion_con_real_a_supabase(mes_predicho: str, ipc_real: float, error_absoluto: float = None):
    """Actualiza una predicción con el dato real"""
    if not supabase_client:
        print("⚠️  Supabase no disponible, actualización no guardada")
        return False

    try:
        supabase_client.table('predicciones_historico').update({
            "ipc_real": ipc_real,
            "error_absoluto": error_absoluto
        }).eq('mes_predicho', mes_predicho).execute()
        print(f"✅ Predicción {mes_predicho} actualizada con dato real en Supabase")
        return True
    except Exception as e:
        print(f"⚠️  Error actualizando predicción en Supabase: {str(e)[:100]}")
        return False

@app.get("/")
def root():
    """Servir index.html"""
    return FileResponse("index.html", media_type="text/html")

@app.get("/metodologia-prediccion")
def metodologia():
    """Servir página de metodología técnica"""
    return FileResponse("metodologia_prediccion.html", media_type="text/html")

@app.get("/boletin-proyeccion")
def boletin():
    """Servir boletín oficial de proyección IPC"""
    return FileResponse("boletin_proyeccion.html", media_type="text/html")

@app.get("/api/predecir")
def predecir(mes: str = None):
    """Endpoint de predicción FRESCA sin cachés - genera datos nuevos cada vez"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        # GENERAR DATOS FRESCOS - sin cachés
        print(f"\n🔄 Generando predicción FRESCA para mes: {mes or 'próximo mes'}")
        resultado = predictor.predict_ipc_for_month(mes) if mes else predictor.predict_ipc_for_month()

        # Headers anti-caché
        from fastapi.responses import JSONResponse
        response = JSONResponse(content=resultado)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predecir-meses")
def predecir_meses(num: int = 3):
    """Predice múltiples meses adelante encadenados"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        if num < 1 or num > 12:
            raise HTTPException(status_code=400, detail="Número de meses debe estar entre 1 y 12")

        resultado = predictor.predict_forward_months(num)
        return {"predicciones": resultado, "total": len(resultado)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predecir-v2")
def predecir_v2():
    """Predicción Ensemble v2.0: Lee desde Supabase (fuente de verdad)"""
    try:
        # LEER directamente de Supabase - es la fuente de verdad
        if supabase_client:
            print("🌐 Leyendo predicción v2.0 desde Supabase...")
            response = supabase_client.table('predicciones_historico').select("*").eq('version', 'v2.0-ensemble').execute()
            data = response.data

            if data and len(data) > 0:
                pred = data[0]
                resultado = {
                    'mes_predicho': pred.get('mes_predicho', '2026-07'),
                    'ensemble_prediccion': pred.get('variacion_esperada', 0.26),
                    'predicciones_por_modelo': {},
                    'pesos': {'ARIMA': 0.40, 'XGBoost': 0.40, 'LSTM': 0.20},
                    'confianza': 0.69,
                    'timestamp': pred.get('timestamp', '')
                }
                print(f"✅ Predicción v2.0 desde Supabase: {resultado['ensemble_prediccion']}%")
            else:
                raise HTTPException(status_code=404, detail="No hay predicción v2.0 en Supabase")
        else:
            # Fallback a advanced_predictor si Supabase no está disponible
            advanced_predictor = AdvancedPredictor()
            resultado = advanced_predictor.predict_ensemble()

            if not resultado:
                raise HTTPException(status_code=500, detail="No hay predicciones disponibles")

        from fastapi.responses import JSONResponse
        response = JSONResponse(content=resultado)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/validar-prediccion-v2")
def validar_prediccion_v2(prediccion_fecha: str, prediccion_valor: float, valor_real: float):
    """Registra predicción v2.0 contra valor real publicado por INE

    Args:
        prediccion_fecha: "Julio 2026"
        prediccion_valor: 0.26 (valor predicho)
        valor_real: 0.28 (valor real de INE)
    """
    try:
        advanced_predictor = AdvancedPredictor()
        advanced_predictor.validate_and_log(
            prediccion_fecha=prediccion_fecha,
            prediccion_valor=prediccion_valor,
            valor_real=valor_real
        )

        perf = advanced_predictor.get_model_performance()

        from fastapi.responses import JSONResponse
        response = JSONResponse(content={
            "success": True,
            "mensaje": f"Predicción de {prediccion_fecha} validada",
            "error": abs(prediccion_valor - valor_real),
            "performance": perf
        })
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analisis")
def analisis():
    """Endpoint de análisis con Groq"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        resultado = predictor.analyze_trend()
        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/datos")
def datos():
    """Obtener datos 2025-01 a 2026-06 desde Banco Central"""
    try:
        # Leer datos_bcch.json (fuente única)
        with open('datos_bcch.json', 'r', encoding='utf-8') as f:
            bcch = json.load(f)

        # Filtrar SOLO 2025-01 a 2026-06
        datos_list = []
        for d in bcch.get('datos_historicos', []):
            mes = d.get('mes', '')
            if '2025-01' <= mes <= '2026-06':
                datos_list.append({
                    "mes": mes,
                    "ipc_percent": float(d.get('indice', 0) - 100),
                    "ipc_index": float(d.get('indice', 0)),
                    "variacion_mensual": float(d.get('var_mensual', 0)),
                    "variacion_12_meses": float(d.get('var_12_meses', 0)) if d.get('var_12_meses') else None
                })

        # Ordenar ASC (antiguos primero)
        datos_list = sorted(datos_list, key=lambda x: x['mes'])

        return {"datos": datos_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/canasta/{mes}")
def canasta_mes(mes: str):
    """Obtener canasta para un mes específico"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        canasta = predictor.get_canasta_composition(mes)
        return {"canasta": canasta if isinstance(canasta, list) else []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/canasta-acumulada")
def canasta_acumulada(mes: str = "2026-06"):
    """Obtener canasta para mes específico (solo 2025-01 a 2026-06)"""
    try:
        # Validar que mes está en rango
        if not ('2025-01' <= mes <= '2026-06'):
            raise HTTPException(status_code=400, detail=f"Mes {mes} fuera de rango (2025-01 a 2026-06)")

        # Leer datos_bcch.json
        with open('datos_bcch.json', 'r', encoding='utf-8') as f:
            bcch = json.load(f)

        # Obtener canasta para ese mes
        canasta_historica = bcch.get('canasta_historica', {})
        acumulado = canasta_historica.get(mes, [])

        if not acumulado:
            # Si no hay canasta específica, usar la canasta actual
            acumulado = bcch.get('divisiones_canasta', [])

        return {"acumulado": acumulado if isinstance(acumulado, list) else []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug-historico")
def debug_historico():
    """DEBUG: Muestra exactamente qué hay en predicciones_historico.json"""
    try:
        import json
        with open("predicciones_historico.json", 'r', encoding='utf-8') as f:
            contenido = json.load(f)

        return {
            "archivo": "predicciones_historico.json",
            "primer_valor_variacion": contenido[0].get("variacion_esperada") if contenido else None,
            "total_entradas": len(contenido),
            "primeros_3_meses": [e.get("mes_predicho", e.get("mes_actual")) for e in contenido[:3]],
            "contenido_completo": contenido
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/historico-predicciones")
def historico_predicciones():
    """Obtener histórico SOLO desde Banco Central (2025-01 a 2026-06)"""
    try:
        from fastapi.responses import JSONResponse

        # Leer datos_bcch.json (fuente única)
        print("📊 Leyendo datos de Banco Central (datos_bcch.json)...")
        with open('datos_bcch.json', 'r', encoding='utf-8') as f:
            bcch = json.load(f)

        # Filtrar SOLO 2025-01 a 2026-06
        historico = []
        for d in bcch.get('datos_historicos', []):
            mes = d.get('mes', '')
            if '2025-01' <= mes <= '2026-06':
                historico.append({
                    "mes": mes,
                    "variacion_mensual": d.get('var_mensual'),
                    "indice": d.get('indice'),
                    "variacion_12_meses": d.get('var_12_meses'),
                    "fuente": "Banco Central",
                    "tipo": "dato-real"
                })

        # Ordenar DESC (más reciente primero)
        historico = sorted(historico, key=lambda x: x['mes'], reverse=True)

        print(f"✅ {len(historico)} meses de datos BC (2025-01 a 2026-06)")

        if not historico:
            raise HTTPException(status_code=404, detail="No hay datos para 2025-01 a 2026-06")

        resp = JSONResponse(content={"historico": historico})
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/desempen-modelo")
def desempen_modelo():
    """Obtener métricas de desempeño del modelo"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        metricas = predictor.get_desempen_modelo()
        return metricas

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/actualizar-prediccion/{mes}")
def actualizar_prediccion(mes: str, ipc_real: float = None):
    """Actualizar una predicción con el valor real publicado"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        if ipc_real is None:
            raise HTTPException(status_code=400, detail="Parámetro ipc_real requerido")

        exito = predictor.actualizar_prediccion_con_real(mes, ipc_real)

        # 💾 GUARDAR dato real a Supabase
        if exito and supabase_client:
            guardar_dato_real_a_supabase(mes, ipc_real)
            # También actualizar la predicción con el error
            actualizar_prediccion_con_real_a_supabase(mes, ipc_real)

        if exito:
            return {"success": True, "mensaje": f"Predicción de {mes} actualizada con IPC real: {ipc_real}"}
        else:
            raise HTTPException(status_code=404, detail=f"No se encontró predicción para {mes}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/datos-ipc-supabase")
def datos_ipc_supabase():
    """Obtener datos IPC desde Supabase + cachea en JSON local"""
    try:
        cache_path = "ipc_datos_cache.json"
        cache_age_minutes = 60  # Cachear por 1 hora

        # Intentar leer desde caché local
        if os.path.exists(cache_path):
            import time
            age = time.time() - os.path.getmtime(cache_path)
            if age < cache_age_minutes * 60:
                print(f"📦 Usando caché local (edad: {int(age/60)} min)")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    from fastapi.responses import JSONResponse
                    cached = json.load(f)
                    response = JSONResponse(content={"datos": cached, "source": "cache"})
                    response.headers["Cache-Control"] = "no-store"
                    return response

        # Si no hay caché o está viejo, leer de Supabase
        if supabase_client:
            print("🌐 Leyendo desde Supabase...")
            response = supabase_client.table('ipc_datos').select("*").order('mes', desc=False).execute()
            datos = response.data if response.data else []

            # Guardar en caché local
            if datos:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, ensure_ascii=False, indent=2)
                print(f"✅ {len(datos)} registros cacheados")

            from fastapi.responses import JSONResponse
            resp = JSONResponse(content={"datos": datos, "source": "supabase"})
            resp.headers["Cache-Control"] = "no-store"
            return resp
        else:
            # Fallback a archivo local si Supabase no disponible
            print("⚠️  Supabase no disponible, usando datos_bcch.json")
            with open('datos_bcch.json', 'r', encoding='utf-8') as f:
                bcch = json.load(f)
                datos = bcch['datos_historicos']

            from fastapi.responses import JSONResponse
            resp = JSONResponse(content={"datos": datos, "source": "local"})
            resp.headers["Cache-Control"] = "no-store"
            return resp

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
