#!/usr/bin/env python3
"""
Endpoint HTTP para actualización de datos macroeconómicos
Funciona en Railway, Vercel, o cualquier servidor HTTP

USAR EN:
- Railway: FastAPI app normal
- Vercel: Serverless function
- Local: python3 app_cron_endpoint.py

LLAMAR DESDE:
- EasyCron (gratis): https://www.easycron.com
- cron-job.org (gratis): https://cron-job.org
- GitHub Actions
- Azure Functions
- AWS Lambda

EJEMPLO URL:
https://tu-app.railway.app/api/actualizar-datos-macro?token=tu_token_secreto
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import os
from datos_macro_manager import DatosMacroManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="IPC Predictor - Cron Endpoint")

# Token secreto para seguridad (cambiar en producción)
CRON_TOKEN = os.getenv("CRON_TOKEN", "tu_token_super_secreto_aqui")


@app.get("/")
async def root():
    """Health check"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/actualizar-datos-macro")
async def actualizar_datos_macro(token: str = Query(...)):
    """
    Endpoint para actualizar datos macroeconómicos

    Requiere parámetro: token=tu_token_secreto

    Ejemplo:
    GET /api/actualizar-datos-macro?token=tu_token_super_secreto_aqui

    Retorna:
    {
        "status": "success",
        "datos_actualizados": 5,
        "timestamp": "2026-07-18T10:30:00",
        "proxima_actualizacion": "2026-07-19T10:30:00"
    }
    """

    # Validar token
    if token != CRON_TOKEN:
        logger.warning(f"❌ Intento de acceso sin autorización desde {token}")
        raise HTTPException(status_code=401, detail="Token inválido")

    logger.info("=" * 60)
    logger.info("🚀 INICIANDO ACTUALIZACIÓN DE DATOS MACROECONÓMICOS (via HTTP)")
    logger.info(f"📅 Fecha/Hora: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    try:
        # Inicializar manager
        manager = DatosMacroManager()

        # Actualizar todos los datos expirados
        exito = manager.actualizar_todos()

        if exito:
            logger.info("✅ ACTUALIZACIÓN EXITOSA")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Datos actualizados correctamente",
                    "timestamp": datetime.now().isoformat(),
                    "ultima_actualizacion": manager.cache.get('ultima_actualizacion'),
                    "proxima_actualizacion": manager.cache.get('prox_actualizacion_programada'),
                }
            )
        else:
            logger.warning("⚠️  ACTUALIZACIÓN PARCIAL")
            return JSONResponse(
                status_code=206,  # Partial Content
                content={
                    "status": "partial",
                    "message": "Algunos datos no se pudieron actualizar",
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.error(f"❌ ERROR: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache-status")
async def cache_status():
    """Ver estado actual del cache (sin autenticación para debugging)"""
    try:
        manager = DatosMacroManager()
        return {
            "ultima_actualizacion": manager.cache.get('ultima_actualizacion'),
            "proxima_actualizacion": manager.cache.get('prox_actualizacion_programada'),
            "version": manager.cache.get('version'),
            "datos_disponibles": len(manager.cache.get('factores_internos', {}).get('datos', [])) +
                                len(manager.cache.get('factores_externos', {}).get('mundo', [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
