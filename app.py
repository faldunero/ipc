#!/usr/bin/env python3
"""API Backend para Predictor IPC - FastAPI"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ipc_predictor import IPCPredictor
import os
import json
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

app = FastAPI(title="Predictor IPC")

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

@app.get("/api/historico-predicciones")
def historico_predicciones():
    """Obtener histórico completo - SIN CACHÉ"""
    try:
        if predictor is None:
            raise HTTPException(status_code=500, detail="Predictor no inicializado")

        historico = predictor.get_historico_predicciones()

        from fastapi.responses import JSONResponse
        response = JSONResponse(content={"historico": historico})
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
