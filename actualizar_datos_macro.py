#!/usr/bin/env python3
"""
Script de Actualización Automática de Datos Macroeconómicos
Ejecutar vía cron/scheduled task: 2 veces al mes (ej: 1ro y 15 de cada mes)

INSTALACIÓN EN LINUX/MAC (crontab):
  0 9 1,15 * * cd /path/to/IPC && python3 actualizar_datos_macro.py >> logs/actualizacion.log 2>&1

INSTALACIÓN EN WINDOWS (Task Scheduler):
  Programa: python.exe
  Argumentos: C:\path\to\actualizar_datos_macro.py
  Frecuencia: Diaria a las 09:00 (pero script interno maneja lógica de actualización)
"""

import os
import sys
import logging
from datetime import datetime
from datos_macro_manager import DatosMacroManager

# Configurar logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'actualizacion.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Ejecuta actualización de datos macroeconómicos"""
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO ACTUALIZACIÓN DE DATOS MACROECONÓMICOS")
    logger.info(f"📅 Fecha/Hora: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    try:
        # Inicializar manager
        manager = DatosMacroManager()

        # Actualizar todos los datos expirados
        exito = manager.actualizar_todos()

        if exito:
            logger.info("✅ ACTUALIZACIÓN EXITOSA")
            logger.info("📊 Estado del cache:")
            logger.info(f"  • Última actualización: {manager.cache.get('ultima_actualizacion')}")
            logger.info(
                f"  • Próxima actualización programada: "
                f"{manager.cache.get('prox_actualizacion_programada')}"
            )
            return 0
        else:
            logger.warning("⚠️  ACTUALIZACIÓN PARCIAL (algunos datos no se pudieron actualizar)")
            return 1

    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    exit_code = main()
    logger.info("=" * 60)
    sys.exit(exit_code)
