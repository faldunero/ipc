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
    """Predicción Ensemble v2.0: ARIMA (40%) + XGBoost (40%) + LSTM (20%)

    Combina 3 modelos avanzados con variables exógenas calendarias.
    Respuesta: ensemble_prediccion (%), predicciones individuales, confianza
    """
    try:
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
    """Obtener últimos 12 datos históricos"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        df = predictor.ipc_data.tail(12)
        datos_list = []
        for idx, row in df.iterrows():
            datos_list.append({
                "mes": row.get('mes', ''),
                "ipc_percent": float(row.get('ipc_index', 0) - 100),
                "ipc_index": float(row.get('ipc_index', 0)),
                "variacion_mensual": float(row.get('variacion_mensual', 0)),
                "variacion_12_meses": float(row.get('variacion_12_meses', 0))
            })
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
    """Obtener canasta acumulada de últimos 12 meses para un mes específico"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        # Usar el mes específico para obtener la canasta
        acumulado = predictor.get_canasta_composition(mes)

        # Renombrar 'indice' a 'indice_promedio' para consistencia
        for item in acumulado:
            if 'indice' in item and 'indice_promedio' not in item:
                item['indice_promedio'] = item['indice']

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
    """Obtener histórico directo del archivo JSON (sin transformaciones)"""
    try:
        # LEER DIRECTAMENTE DEL ARCHIVO - es la fuente de verdad
        import json
        historico_path = "predicciones_historico.json"

        if not os.path.exists(historico_path):
            raise HTTPException(status_code=404, detail="Histórico no encontrado")

        with open(historico_path, 'r', encoding='utf-8') as f:
            historico = json.load(f)

        from fastapi.responses import JSONResponse
        response = JSONResponse(content={"historico": historico})
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        print(f"✅ Histórico leído: primer valor = {historico[0].get('variacion_esperada')}%")
        return response

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
