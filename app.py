#!/usr/bin/env python3
"""API Backend para Predictor IPC - FastAPI"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ipc_predictor import IPCPredictor
from advanced_predictor import AdvancedPredictor
from arimax_predictor import ARIMAXPredictor
import os
import json
from dotenv import load_dotenv
from datetime import datetime

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

def cargar_canasta_real():
    """Carga datos reales de canasta IPC"""
    from pathlib import Path
    try:
        canasta_file = Path("canasta_real.json")
        if canasta_file.exists():
            with open(canasta_file, 'r', encoding='utf-8') as f:
                canasta = json.load(f)
            print(f"✅ Canasta real cargada ({canasta.get('timestamp', 'sin fecha')})")
            return canasta
        else:
            print("⚠️  canasta_real.json no encontrado")
            return None
    except Exception as e:
        print(f"⚠️  Error cargando canasta: {e}")
        return None

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

@app.get("/fuentes-datos")
@app.get("/fuentes-datos.html")
def fuentes_datos():
    """Servir página de fuentes de datos"""
    return FileResponse("fuentes-datos.html", media_type="text/html")

@app.get("/metodologia-prediccion")
def metodologia():
    """Servir página de metodología técnica"""
    return FileResponse("metodologia_prediccion.html", media_type="text/html")

@app.get("/boletin-proyeccion")
def boletin():
    """Servir boletín oficial de proyección IPC"""
    return FileResponse("boletin_proyeccion.html", media_type="text/html")

@app.get("/dashboard-entrenamiento")
def dashboard_entrenamiento():
    """Servir dashboard de entrenamiento en tiempo real"""
    return FileResponse("dashboard-entrenamiento.html", media_type="text/html")

@app.get("/dashboard-entrenamiento.html")
def dashboard_entrenamiento_html():
    """Servir dashboard (ruta alternativa con .html)"""
    return FileResponse("dashboard-entrenamiento.html", media_type="text/html")

@app.get("/logs")
def logs_dashboard():
    """Servir dashboard de logs"""
    return FileResponse("logs_dashboard.html", media_type="text/html")

@app.get("/logs_dashboard.html")
def logs_dashboard_html():
    """Servir dashboard de logs (ruta alternativa)"""
    return FileResponse("logs_dashboard.html", media_type="text/html")

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

@app.post("/api/actualizar-prediccion-arimax")
def actualizar_prediccion_arimax():
    """Ejecuta recolección + predicción ARIMAX dinámica (llamable desde UI)"""
    try:
        import subprocess
        from pathlib import Path
        import os

        logger.info("🔄 POST: Actualizando predicción ARIMAX...")

        # 1. Ejecutar recolector
        logger.info("Step 1: Recolectando datos...")
        resultado_recolector = subprocess.run(
            ['python3', 'recolector_diario_completo.py'],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=60
        )
        if resultado_recolector.returncode != 0:
            logger.warning(f"⚠️ Recolector: {resultado_recolector.stderr[:200]}")

        # 2. Ejecutar predictor dinámico
        logger.info("Step 2: Prediciendo mes actual...")
        resultado_predictor = subprocess.run(
            ['python3', 'arimax_predictor_dinamico.py'],
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=120
        )
        if resultado_predictor.returncode != 0:
            logger.error(f"❌ Predictor: {resultado_predictor.stderr}")
            raise Exception(f"Error en predictor: {resultado_predictor.stderr}")

        # 3. Cargar predicción generada
        prediccion_path = Path('prediccion_actual.json')
        if prediccion_path.exists():
            with open(prediccion_path, 'r', encoding='utf-8') as f:
                prediccion = json.load(f)

            logger.info(f"✅ Predicción generada: {prediccion['prediccion']:.4f}%")

            respuesta = {
                'success': True,
                'prediccion': prediccion['prediccion'],
                'intervalo_confianza': prediccion['intervalo_confianza'],
                'completitud': prediccion['completitud'],
                'nivel_confianza': prediccion['nivel_confianza'],
                'timestamp': datetime.now().isoformat(),
                'mensaje': f"Predicción actualizada: {prediccion['prediccion']:.4f}% (Confianza: {prediccion['nivel_confianza']})"
            }

            resp = JSONResponse(content=respuesta)
            resp.headers["Cache-Control"] = "no-cache"
            return resp
        else:
            raise Exception("No se generó prediccion_actual.json")

    except Exception as e:
        logger.error(f"❌ Error actualizando predicción: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predecir-arimax")
def predecir_arimax():
    """Predicción ARIMAX: usa datos REALES diarios como variables exógenas"""
    try:
        print("🔮 Prediciendo con ARIMAX + variables exógenas REALES...")

        # Cargar variables exógenas REALES de hoy
        try:
            with open('exogenas_actuales.json', 'r', encoding='utf-8') as f:
                exogenas_reales = json.load(f)
        except:
            exogenas_reales = {
                'dolar': 913.86,
                'tpm': 4.5,
                'uf': 40844.79,
                'timestamp': datetime.now().isoformat()
            }

        # Ejecutar ARIMAX
        predictor_arimax = ARIMAXPredictor()

        if not predictor_arimax.fetch_datos_historicos():
            raise HTTPException(status_code=500, detail="No hay datos históricos")

        # Usar datos exógenos REALES
        predictor_arimax.exogenas = {
            'dolar': exogenas_reales.get('dolar', 913),
            'tpm': exogenas_reales.get('tpm', 4.5)
        }

        if not predictor_arimax.construir_matriz_exogenas():
            raise HTTPException(status_code=500, detail="Error construyendo matriz")

        # Entrenar y predecir
        resultado_pred = predictor_arimax.predecir_mes_actual(order=(1, 1, 1))

        if not resultado_pred:
            raise HTTPException(status_code=500, detail="Error en predicción ARIMAX")

        # Formatear respuesta
        respuesta = {
            'modelo': 'ARIMAX',
            'prediccion': resultado_pred['prediccion'],
            'intervalo_confianza': resultado_pred['intervalo_confianza'],
            'variables_exogenas_usadas': predictor_arimax.exogenas,
            'timestamp_datos': exogenas_reales.get('timestamp'),
            'timestamp_prediccion': datetime.now().isoformat(),
            'fuente': 'arimax-datos-reales'
        }

        print(f"✅ Predicción ARIMAX: {resultado_pred['prediccion']:.4f}% (IC: [{resultado_pred['intervalo_confianza']['min']:.4f}%, {resultado_pred['intervalo_confianza']['max']:.4f}%])")
        print(f"   Con dólar: ${predictor_arimax.exogenas['dolar']:.2f}, TPM: {predictor_arimax.exogenas['tpm']:.2f}%")

        resp = JSONResponse(content=respuesta)
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    except Exception as e:
        print(f"❌ Error en predecir_arimax: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predecir-v2")
def predecir_v2(regenerar: bool = False):
    """Predicción Ensemble v2.0: Regenera con indicadores adelantados si `regenerar=true`"""
    try:
        from pathlib import Path
        from datetime import datetime, timedelta
        import os

        cache_file = Path("prediccion_cache_v2.json")

        # Si se solicita regenerar, hacerlo ahora
        if regenerar:
            print("🔄 Regenerando predicción con indicadores adelantados + canasta REAL...")
            from advanced_forecasting import AdvancedForecaster
            from fetch_all_indicators import consolidar_todos_indicadores
            from fetch_external_data import consolidar_datos_exogenos

            # Recolectar datos nuevos
            indicadores = consolidar_todos_indicadores()
            datos_exogenos = consolidar_datos_exogenos()
            canasta_real = cargar_canasta_real()  # CARGAR DATOS REALES DE CANASTA

            # Cargar histórico
            with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
                historico = json.load(f)
                historico_ipc = [h.get('variacion_12_meses', 0) for h in reversed(historico)][:13]

            # Generar predicción con indicadores
            forecaster = AdvancedForecaster()
            resultado = forecaster.forecast_ensemble_avanzado(
                historico_ipc,
                datos_exogenos,
                indicadores
            )

            # Agregar datos de canasta a la respuesta
            if canasta_real:
                resultado['canasta_real'] = {
                    'timestamp': canasta_real.get('timestamp'),
                    'categorias': list(canasta_real.get('canasta', {}).keys()),
                    'fuentes': list(set([
                        d.get('fuente', 'desconocida')
                        for cat in canasta_real.get('canasta', {}).values()
                        for d in ([cat] if isinstance(cat, dict) else [cat.get('fuente', {})])
                    ]))
                }

            # Guardar en cache
            resultado['fuente'] = 'regenerada-con-indicadores-y-canasta-real'
            resultado['timestamp_regeneracion'] = datetime.now().isoformat()

            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(resultado, f, ensure_ascii=False, indent=2)
                print(f"✅ Predicción regenerada: {resultado['prediccion_ensemble']}%")
            except Exception as e:
                print(f"⚠️ Error guardando: {e}")

            from fastapi.responses import JSONResponse
            resp = JSONResponse(content=resultado)
            resp.headers["Cache-Control"] = "public, max-age=86400"
            return resp

        # 1. INTENTAR LEER DE CACHE LOCAL (si existe y es reciente)
        if cache_file.exists():
            age_seconds = datetime.now().timestamp() - os.path.getmtime(cache_file)
            age_hours = age_seconds / 3600

            if age_hours < 24:  # Cache válido por 24 horas
                print(f"✅ Cache válido (edad: {age_hours:.1f} horas)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    resultado = json.load(f)
                    resultado['fuente'] = 'cache-local'
                    resultado['edad_cache_horas'] = round(age_hours, 1)

                    # Asegurar que tiene ensemble_prediccion
                    if 'ensemble_prediccion' not in resultado and 'prediccion_ensemble' in resultado:
                        resultado['ensemble_prediccion'] = resultado['prediccion_ensemble']

                    from fastapi.responses import JSONResponse
                    resp = JSONResponse(content=resultado)
                    resp.headers["Cache-Control"] = "public, max-age=86400"  # 24 horas
                    return resp
            else:
                print(f"⏰ Cache expirado (edad: {age_hours:.1f} horas)")

        # 2. SI NO HAY CACHE O EXPIRÓ - LEER DE SUPABASE
        if supabase_client:
            print("🌐 Leyendo predicción v2.0 desde Supabase...")
            response = supabase_client.table('predicciones_historico').select("*").eq('version', 'v2.0-ensemble').execute()
            data = response.data

            if data and len(data) > 0:
                pred = data[0]
                valor_pred = float(pred.get('variacion_esperada', 0.26))
                resultado = {
                    'mes_predicho': pred.get('mes_predicho', '2026-07'),
                    'ensemble_prediccion': valor_pred,
                    'prediccion_ensemble': valor_pred,  # Ambos formatos
                    'predicciones_por_modelo': {},
                    'pesos': {'ARIMA': 0.40, 'XGBoost': 0.40, 'LSTM': 0.20},
                    'confianza': 0.69,
                    'timestamp': pred.get('timestamp', ''),
                    'fuente': 'supabase'
                }
                print(f"✅ Predicción v2.0 desde Supabase: {resultado['ensemble_prediccion']}%")

                # Guardar en cache local
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(resultado, f, ensure_ascii=False, indent=2)
                    print(f"💾 Predicción guardada en cache local")
                except Exception as e:
                    print(f"⚠️ Error guardando cache: {e}")

            else:
                raise HTTPException(status_code=404, detail="No hay predicción v2.0 en Supabase")
        else:
            # Fallback a advanced_predictor si Supabase no está disponible
            advanced_predictor = AdvancedPredictor()
            resultado = advanced_predictor.predict_ensemble()

            if not resultado:
                raise HTTPException(status_code=500, detail="No hay predicciones disponibles")

            resultado['fuente'] = 'advanced-predictor'

            # Guardar en cache
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(resultado, f, ensure_ascii=False, indent=2)
            except:
                pass

        from fastapi.responses import JSONResponse
        resp = JSONResponse(content=resultado)
        resp.headers["Cache-Control"] = "public, max-age=86400"  # 24 horas
        return resp

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/regenerar-prediccion")
def regenerar_prediccion():
    """Regenera la predicción con indicadores adelantados + canasta REAL AHORA"""
    try:
        print("🔄 POST: Regenerando predicción con indicadores adelantados + canasta REAL...")
        from advanced_forecasting import AdvancedForecaster
        from fetch_all_indicators import consolidar_todos_indicadores
        from fetch_external_data import consolidar_datos_exogenos
        from pathlib import Path
        from datetime import datetime

        # Recolectar datos nuevos
        indicadores = consolidar_todos_indicadores()
        datos_exogenos = consolidar_datos_exogenos()
        canasta_real = cargar_canasta_real()  # CARGAR DATOS REALES DE CANASTA

        # Cargar histórico
        with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
            historico = json.load(f)
            historico_ipc = [h.get('variacion_12_meses', 0) for h in reversed(historico)][:13]

        # Generar predicción con indicadores
        forecaster = AdvancedForecaster()
        resultado = forecaster.forecast_ensemble_avanzado(
            historico_ipc,
            datos_exogenos,
            indicadores
        )

        # Agregar datos de canasta a la respuesta
        if canasta_real:
            resultado['canasta_real_usada'] = {
                'timestamp': canasta_real.get('timestamp'),
                'alimentos_promedio': canasta_real.get('canasta', {}).get('alimentos', {}).get('promedio'),
                'transporte_promedio': canasta_real.get('canasta', {}).get('transporte', {}).get('promedio'),
                'combustibles': canasta_real.get('canasta', {}).get('combustibles')
            }
            print(f"📊 Canasta real integrada en predicción")

        # Guardar en cache
        cache_file = Path("prediccion_cache_v2.json")
        resultado['fuente'] = 'regenerada-con-indicadores-y-canasta-real'
        resultado['timestamp_regeneracion'] = datetime.now().isoformat()

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

        print(f"✅ Predicción regenerada: {resultado['prediccion_ensemble']}%")

        return {
            "status": "success",
            "mensaje": f"Predicción regenerada: {resultado['prediccion_ensemble']}%",
            "prediccion": resultado['prediccion_ensemble'],
            "intervalo": resultado['intervalo_confianza_95'],
            "timestamp": resultado['timestamp_regeneracion']
        }

    except Exception as e:
        print(f"❌ Error regenerando: {e}")
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
    """Obtener datos 2025-01 en adelante desde Banco Central"""
    try:
        # Leer datos_bcch.json (fuente única)
        with open('datos_bcch.json', 'r', encoding='utf-8') as f:
            bcch = json.load(f)

        # Filtrar SOLO 2025-01 en adelante
        datos_list = []
        for d in bcch.get('datos_historicos', []):
            mes = d.get('mes', '')
            if '2025-01' <= mes:  # Sin límite superior, trae todos los datos
                # Usar campos correctos: ipc_var_mensual, ipc_var_12m
                var_mensual = float(d.get('ipc_var_mensual', 0))
                var_12m = d.get('ipc_var_12m')
                datos_list.append({
                    "mes": mes,
                    "ipc_percent": var_mensual,  # Variación mensual, no índice
                    "ipc_index": var_mensual,    # Para compatibilidad
                    "variacion_mensual": var_mensual,
                    "variacion_12_meses": float(var_12m) if var_12m is not None else None
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
    """Obtener canasta para mes específico (2025-01 en adelante)"""
    try:
        # Validar que mes está en rango
        if not ('2025-01' <= mes):  # Sin límite superior
            raise HTTPException(status_code=400, detail=f"Mes {mes} fuera de rango (2025-01 en adelante)")

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
    """Obtener histórico COMBINADO: predicciones + realidad"""
    try:
        from fastapi.responses import JSONResponse
        import os
        import time

        cache_path = "historico_predicciones_cache.json"
        cache_age_minutes = 5  # Cachear solo 5 minutos (datos se actualizan diariamente)

        # 1️⃣ INTENTAR LEER DESDE CACHÉ LOCAL (más rápido)
        if os.path.exists(cache_path):
            age = time.time() - os.path.getmtime(cache_path)
            if age < cache_age_minutes * 60:
                print(f"📦 Caché válido (edad: {int(age/60)} min)")
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    resp = JSONResponse(content={"historico": cached, "source": "cache"})
                    resp.headers["Cache-Control"] = "public, max-age=300"  # 5 minutos
                    return resp
            else:
                print(f"⏰ Caché expirado (edad: {int(age/60)} min > {cache_age_minutes})")

        # 2️⃣ CACHÉ EXPIRADO O NO EXISTE - CARGAR DE FUENTE
        historico = []
        validaciones_dict = {}

        # Cargar validaciones en dict para merge
        if os.path.exists('historico_validaciones.json'):
            print("📥 Cargando validaciones desde historico_validaciones.json...")
            with open('historico_validaciones.json', 'r', encoding='utf-8') as f:
                validaciones = json.load(f)
                for v in validaciones:
                    validaciones_dict[v.get('mes', '')] = v

        # Cargar 36 meses desde datos_historicos_36m.json (fuente principal)
        if os.path.exists('datos_historicos_36m.json'):
            print("📥 Cargando 36 meses desde datos_historicos_36m.json...")
            with open('datos_historicos_36m.json', 'r', encoding='utf-8') as f:
                datos_historicos = json.load(f)

                for d in datos_historicos:
                    mes = d.get('mes', '')
                    # Combinar datos históricos + validaciones si existen
                    val = validaciones_dict.get(mes, {})

                    historico.append({
                        "mes": mes,
                        "prediccion": float(val.get('prediccion', 0)),
                        "prediccion_ensemble": float(val.get('prediccion', 0)),
                        "real": float(val.get('ipc_real', d.get('ipc_var_mensual', 0))),  # Usa validación si existe, sino histórico
                        "variacion_mensual_real": float(d.get('ipc_var_mensual', 0)),
                        "variacion_12_meses": float(d.get('ipc_var_12m', 0)),
                        "error": float(val.get('error_pp', 0)),
                        "error_absoluto": float(val.get('error_pp', 0)),
                        "dentro_intervalo_confianza": val.get('dentro_ic', False),
                        "nivel_confianza": 'VALIDADO' if mes in validaciones_dict else 'HISTÓRICO',
                        "completitud": val.get('completitud', 'N/A'),
                        "validacion_fecha": val.get('validacion_fecha', '')
                    })
        else:
            print("⚠️ datos_historicos_36m.json no existe")

        # Ordenar DESC (más reciente primero)
        historico = sorted(historico, key=lambda x: x.get('mes', ''), reverse=True)

        if not historico:
            raise HTTPException(status_code=404, detail="No hay datos disponibles")

        # 3️⃣ GUARDAR EN CACHÉ PARA PRÓXIMAS LLAMADAS
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(historico, f, ensure_ascii=False, indent=2)
            print(f"✅ {len(historico)} meses guardados en caché (7 días TTL)")
        except Exception as cache_err:
            print(f"⚠️  Error guardando caché: {cache_err}")

        # 4️⃣ RETORNAR CON HEADERS DE CACHÉ
        resp = JSONResponse(content={"historico": historico, "source": "fresh"})
        resp.headers["Cache-Control"] = "public, max-age=300"  # 5 minutos
        resp.headers["Pragma"] = ""
        return resp

    except Exception as e:
        print(f"❌ Error en historico_predicciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs/hoy")
def obtener_logs_hoy():
    """Obtiene logs de ejecución de hoy con resumen"""
    try:
        from pathlib import Path
        from datetime import datetime
        import os

        # Crear directorio si no existe
        log_dir = Path("logs")
        try:
            log_dir.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            print(f"⚠️ No se pudo crear directorio logs: {e}")

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        archivo = log_dir / f"ejecucion_{fecha_hoy}.json"

        # Verificar si archivo existe
        archivo_existe = False
        try:
            archivo_existe = archivo.exists() and os.path.getsize(archivo) > 0
        except:
            archivo_existe = False

        if archivo_existe:
            with open(archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            # Agregar resumen
            resumen = {
                'fecha': fecha_hoy,
                'total_eventos': len(datos.get('eventos', [])),
                'datos_recolectados': len(datos.get('datos_recolectados', {})),
                'modelos_entrenados': len(datos.get('modelos_entrenados', {})),
                'predicciones': len(datos.get('predicciones', {})),
                'errores': len(datos.get('errores', [])),
                'fuentes': list(datos.get('datos_recolectados', {}).keys()),
                'modelos': list(datos.get('modelos_entrenados', {}).keys()),
            }

            datos['resumen'] = resumen
            resp = JSONResponse(content=datos)
            resp.headers["Cache-Control"] = "no-cache"
            return resp
        else:
            # Retornar datos ejemplo si no existe el archivo
            datos_ejemplo = {
                'fecha': fecha_hoy,
                'timestamp_inicio': datetime.now().isoformat(),
                'timestamp_actualizacion': datetime.now().isoformat(),
                'resumen': {
                    'fecha': fecha_hoy,
                    'total_eventos': 10,
                    'datos_recolectados': 5,
                    'modelos_entrenados': 3,
                    'predicciones': 1,
                    'errores': 0,
                    'fuentes': ['SVS', 'INE', 'ASEA', 'Banco Central', 'bencinaenlinea.cl'],
                    'modelos': ['ARIMA', 'XGBoost', 'LSTM'],
                },
                'datos_recolectados': {
                    'SVS': {'cantidad': 4, 'detalles': {'seguros_auto': 450000, 'seguros_vida': 120000}},
                    'INE': {'cantidad': 6, 'detalles': {'alimentos': 118.5, 'transporte': 115.2}},
                    'ASEA': {'cantidad': 3, 'detalles': {'prima_total': 12500000000}},
                    'Banco Central': {'cantidad': 4, 'detalles': {'TPM': 6.50, 'TC': 820}},
                    'bencinaenlinea.cl': {'cantidad': 2, 'detalles': {'bencina_95': 1150, 'diesel': 1080}}
                },
                'modelos_entrenados': {
                    'ARIMA': {'mae': 0.3552, 'rmse': 0.4869},
                    'XGBoost': {'mae': 0.32, 'rmse': 0.45},
                    'LSTM': {'mae': 0.38, 'rmse': 0.51}
                },
                'predicciones': {
                    '2026-09': {'valor': 2.90, 'intervalo': {'min': 2.30, 'max': 3.50}}
                },
                'errores': [],
                'nota': 'Datos de ejemplo. Los logs reales se generan después de ejecutar el pipeline.'
            }

            resp = JSONResponse(content=datos_ejemplo)
            resp.headers["Cache-Control"] = "no-cache"
            return resp

            resp = JSONResponse(content=datos_ejemplo)
            resp.headers["Cache-Control"] = "no-cache"
            return resp

    except Exception as e:
        print(f"⚠️ Error en obtener_logs_hoy: {e}")
        # Devolver datos de ejemplo en lugar de error
        from datetime import datetime as dt
        datos_ejemplo = {
            'fecha': dt.now().strftime('%Y-%m-%d'),
            'timestamp_inicio': dt.now().isoformat(),
            'timestamp_actualizacion': dt.now().isoformat(),
            'resumen': {
                'fecha': dt.now().strftime('%Y-%m-%d'),
                'total_eventos': 10,
                'datos_recolectados': 5,
                'modelos_entrenados': 3,
                'predicciones': 1,
                'errores': 0,
                'fuentes': ['SVS', 'INE', 'ASEA', 'Banco Central', 'bencinaenlinea.cl'],
                'modelos': ['ARIMA', 'XGBoost', 'LSTM'],
            },
            'error': str(e),
            'nota': 'Datos de ejemplo. Para ver logs reales, ejecuta run_pipeline_manual.py'
        }

        from fastapi.responses import JSONResponse
        resp = JSONResponse(content=datos_ejemplo)
        resp.headers["Cache-Control"] = "no-cache"
        return resp

@app.get("/api/logs/historial")
def obtener_historial_logs(dias: int = 30):
    """Obtiene historial de logs últimos N días"""
    try:
        from pathlib import Path
        from datetime import datetime, timedelta

        log_dir = Path("logs")
        historial = []

        for i in range(dias):
            fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            archivo = log_dir / f"ejecucion_{fecha}.json"

            if archivo.exists():
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        historial.append({
                            'fecha': fecha,
                            'eventos': len(data.get('eventos', [])),
                            'errores': len(data.get('errores', [])),
                            'predicciones': len(data.get('predicciones', [])),
                            'datos_fuentes': len(data.get('datos_recolectados', {}))
                        })
                except:
                    pass

        return {"historial": historial, "total_dias": len(historial)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecast-avanzado")
def forecast_avanzado():
    """Forecast avanzado con TODOS los indicadores adelantados"""
    try:
        from advanced_forecasting import AdvancedForecaster
        from fetch_external_data import consolidar_datos_exogenos
        from fetch_all_indicators import consolidar_todos_indicadores
        import json

        print("📊 Recolectando TODOS los indicadores adelantados...")

        # 1. Datos exógenos básicos
        datos_exogenos = consolidar_datos_exogenos()

        # 2. Indicadores adelantados (SVS, INE, ASEA, BC)
        indicadores = consolidar_todos_indicadores()

        # 3. Cargar histórico real
        with open('predicciones_historico.json', 'r', encoding='utf-8') as f:
            historico = json.load(f)
            historico_ipc = [h.get('variacion_12_meses', 0) for h in reversed(historico)][:13]

        # 4. Forecasting avanzado con indicadores
        forecaster = AdvancedForecaster()
        resultado = forecaster.forecast_ensemble_avanzado(
            historico_ipc,
            datos_exogenos,
            indicadores  # Pasar indicadores adelantados
        )

        # 5. Agregar indicadores al resultado
        resultado['indicadores_adelantados'] = indicadores.get('indicador_adelantado', {})
        resultado['fuentes_datos'] = ['SVS', 'INE', 'ASEA', 'BC', 'bencinaenlinea.cl']

        from fastapi.responses import JSONResponse
        resp = JSONResponse(content=resultado)
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return resp

    except Exception as e:
        print(f"❌ Error en forecast_avanzado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ultima-actualizacion")
def ultima_actualizacion():
    """Obtener info de la última actualización y entrenamiento"""
    try:
        import os
        from datetime import datetime

        resultado = {
            "ultima_actualizacion": None,
            "entrenamiento": {
                "total_predicciones": 0,
                "mae": None,
                "rmse": None,
                "aciertos_direccion": "0/0",
                "pct_acierto": 0
            },
            "datos_bc": {
                "meses": 0,
                "rango": "2025-01 en adelante"
            }
        }

        # Leer timestamp de datos_bcch.json
        if os.path.exists('datos_bcch.json'):
            with open('datos_bcch.json', 'r', encoding='utf-8') as f:
                bcch = json.load(f)
                resultado["ultima_actualizacion"] = bcch.get('fecha_actualizacion', 'Desconocida')
                resultado["datos_bc"]["meses"] = len([d for d in bcch.get('datos_historicos', []) if '2025-01' <= d.get('mes', '')])  # Sin límite superior, trae todos los datos

        # Leer resultados del entrenamiento
        if os.path.exists('backtest_proper_resultados.json'):
            with open('backtest_proper_resultados.json', 'r', encoding='utf-8') as f:
                resultados = json.load(f)
                stats = resultados.get('stats', {})
                resultado["entrenamiento"]["total_predicciones"] = stats.get('total', 0)
                resultado["entrenamiento"]["mae"] = stats.get('mae')
                resultado["entrenamiento"]["rmse"] = stats.get('rmse')
                resultado["entrenamiento"]["aciertos_direccion"] = f"{stats.get('aciertos_direccion', 0)}/{stats.get('total', 0)}"
                resultado["entrenamiento"]["pct_acierto"] = stats.get('pct_acierto', 0)

        return resultado
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

@app.post("/api/forzar-entrenamiento")
def forzar_entrenamiento():
    """Forzar reentrenamiento de modelos (ejecuta backtest_proper.py)"""
    try:
        import subprocess

        print("🔄 Iniciando reentrenamiento forzado de modelos...")

        # Ejecutar backtest_proper.py
        resultado = subprocess.run(
            ["python3", "backtest_proper.py"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if resultado.returncode == 0:
            print("✅ Reentrenamiento exitoso")

            # Ejecutar integrate_real_ipc_data.py para sincronizar
            subprocess.run(
                ["python3", "integrate_real_ipc_data.py"],
                capture_output=True,
                timeout=60
            )

            return {
                "status": "success",
                "mensaje": "✅ Reentrenamiento completado exitosamente",
                "detalles": resultado.stdout
            }
        else:
            print(f"❌ Error en reentrenamiento: {resultado.stderr}")
            return {
                "status": "error",
                "mensaje": "❌ Error durante el reentrenamiento",
                "error": resultado.stderr
            }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "mensaje": "⏱️ Reentrenamiento tomó demasiado tiempo (>5 min)"
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            "status": "error",
            "mensaje": f"❌ Error: {str(e)}"
        }

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

@app.get("/api/historico-validaciones")
def historico_validaciones():
    """Obtener histórico de validaciones: predicciones vs realidad"""
    try:
        if os.path.exists('historico_validaciones.json'):
            with open('historico_validaciones.json', 'r', encoding='utf-8') as f:
                validaciones = json.load(f)
            print(f"✅ Histórico de validaciones cargado ({len(validaciones)} meses)")
        else:
            validaciones = []
            print("⚠️  historico_validaciones.json no existe")

        resp = JSONResponse(content=validaciones)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        print(f"❌ Error cargando validaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predicciones-por-categoria")
def predicciones_por_categoria():
    """Obtener predicciones por categoría del mes actual"""
    try:
        if os.path.exists('predicciones_por_categoria.json'):
            with open('predicciones_por_categoria.json', 'r', encoding='utf-8') as f:
                predicciones = json.load(f)
            print(f"✅ Predicciones por categoría cargadas")
        else:
            predicciones = {}
            print("⚠️  predicciones_por_categoria.json no existe")

        resp = JSONResponse(content=predicciones)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        print(f"❌ Error cargando predicciones por categoría: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prediccion-actual")
def prediccion_actual():
    """Obtener predicción actual del mes en curso"""
    try:
        if os.path.exists('prediccion_actual.json'):
            with open('prediccion_actual.json', 'r', encoding='utf-8') as f:
                prediccion = json.load(f)
            print(f"✅ Predicción actual cargada: {prediccion.get('mes')} ({prediccion.get('prediccion'):.4f}%)")
        else:
            prediccion = {"error": "prediccion_actual.json no existe"}
            print("⚠️  prediccion_actual.json no existe")

        resp = JSONResponse(content=prediccion)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    except Exception as e:
        print(f"❌ Error cargando predicción actual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
