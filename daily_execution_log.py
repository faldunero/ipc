#!/usr/bin/env python3
"""
Sistema de registro diario: Audita todo lo que se ejecuta y carga
- Datos recolectados
- Modelos entrenados
- Predicciones generadas
- Errores y alertas
"""

import json
import os
from datetime import datetime, timedelta
import logging
from pathlib import Path

# ============================================================================
# LOGGER GLOBAL
# ============================================================================

def setup_logging():
    """Configura logging a archivo y consola"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Nombre del archivo: YYYY-MM-DD.log
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# CLASE: EXECUTION LOG
# ============================================================================

class ExecutionLog:
    """Registra auditoría de ejecuciones diarias"""

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.execution_file = self.log_dir / f"ejecucion_{self.today}.json"
        self.stats_file = self.log_dir / "estadisticas_mensuales.json"
        self.load_or_create()

    def load_or_create(self):
        """Carga o crea archivo de ejecución del día"""
        if self.execution_file.exists():
            with open(self.execution_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'fecha': self.today,
                'timestamp_inicio': datetime.now().isoformat(),
                'eventos': [],
                'datos_recolectados': {},
                'modelos_entrenados': {},
                'predicciones': {},
                'errores': [],
                'estadisticas': {}
            }

    def save(self):
        """Guarda el log a archivo"""
        self.data['timestamp_actualizacion'] = datetime.now().isoformat()
        with open(self.execution_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Log guardado: {self.execution_file}")

    def registrar_evento(self, tipo, descripcion, detalles=None):
        """Registra un evento en el log"""
        evento = {
            'timestamp': datetime.now().isoformat(),
            'tipo': tipo,  # 'info', 'warning', 'error', 'success'
            'descripcion': descripcion,
            'detalles': detalles or {}
        }
        self.data['eventos'].append(evento)

        # También log en consola
        if tipo == 'error':
            logger.error(f"❌ {descripcion}")
        elif tipo == 'warning':
            logger.warning(f"⚠️ {descripcion}")
        elif tipo == 'success':
            logger.info(f"✅ {descripcion}")
        else:
            logger.info(f"ℹ️ {descripcion}")

    def registrar_datos_recolectados(self, fuente, cantidad, detalles=None):
        """Registra datos recolectados"""
        self.data['datos_recolectados'][fuente] = {
            'timestamp': datetime.now().isoformat(),
            'cantidad': cantidad,
            'detalles': detalles or {}
        }
        self.registrar_evento(
            'success',
            f"Datos recolectados de {fuente}",
            {'cantidad': cantidad}
        )

    def registrar_modelo_entrenado(self, modelo_nombre, metricas):
        """Registra entrenamiento de modelo"""
        self.data['modelos_entrenados'][modelo_nombre] = {
            'timestamp': datetime.now().isoformat(),
            'metricas': metricas
        }
        self.registrar_evento(
            'success',
            f"Modelo {modelo_nombre} entrenado",
            metricas
        )

    def registrar_prediccion(self, mes, valor, intervalo_confianza=None):
        """Registra predicción generada"""
        self.data['predicciones'][mes] = {
            'timestamp': datetime.now().isoformat(),
            'valor': valor,
            'intervalo_confianza': intervalo_confianza
        }
        self.registrar_evento(
            'success',
            f"Predicción generada para {mes}: {valor}%",
            {'mes': mes, 'valor': valor}
        )

    def registrar_error(self, modulo, error_mensaje):
        """Registra error"""
        error = {
            'timestamp': datetime.now().isoformat(),
            'modulo': modulo,
            'mensaje': error_mensaje
        }
        self.data['errores'].append(error)
        self.registrar_evento('error', f"Error en {modulo}: {error_mensaje}")

    def agregar_estadistica(self, clave, valor):
        """Agrega estadística al log"""
        self.data['estadisticas'][clave] = {
            'timestamp': datetime.now().isoformat(),
            'valor': valor
        }

    def generar_resumen(self):
        """Genera resumen de ejecución del día"""
        resumen = {
            'fecha': self.today,
            'total_eventos': len(self.data['eventos']),
            'total_datos_recolectados': sum(
                d.get('cantidad', 0) for d in self.data['datos_recolectados'].values()
            ),
            'total_modelos_entrenados': len(self.data['modelos_entrenados']),
            'total_predicciones': len(self.data['predicciones']),
            'total_errores': len(self.data['errores']),
            'fuentes_datos': list(self.data['datos_recolectados'].keys()),
            'modelos': list(self.data['modelos_entrenados'].keys()),
            'duracion_minutos': (
                (datetime.fromisoformat(self.data.get('timestamp_actualizacion', self.data['timestamp_inicio']))
                - datetime.fromisoformat(self.data['timestamp_inicio'])).total_seconds() / 60
            )
        }
        return resumen

    def exportar_csv(self):
        """Exporta eventos a CSV para análisis"""
        import csv
        csv_file = self.log_dir / f"ejecucion_{self.today}.csv"

        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['timestamp', 'tipo', 'descripcion', 'detalles']
                )
                writer.writeheader()
                for evento in self.data['eventos']:
                    writer.writerow({
                        'timestamp': evento['timestamp'],
                        'tipo': evento['tipo'],
                        'descripcion': evento['descripcion'],
                        'detalles': json.dumps(evento['detalles'])
                    })
            logger.info(f"✅ CSV exportado: {csv_file}")
            return str(csv_file)
        except Exception as e:
            logger.error(f"❌ Error exportando CSV: {e}")
            return None

# ============================================================================
# FUNCIONES DE REGISTRO
# ============================================================================

def log_ejecucion_diaria():
    """Función llamada al inicio de cada actualización diaria"""
    log = ExecutionLog()

    logger.info("\n" + "="*70)
    logger.info(f"🚀 INICIO DE EJECUCIÓN DIARIA - {datetime.now().isoformat()}")
    logger.info("="*70)

    log.registrar_evento('info', 'Inicio de ejecución diaria')

    return log

def log_resumen_final(log):
    """Genera resumen final de ejecución"""
    resumen = log.generar_resumen()

    logger.info("\n" + "="*70)
    logger.info("📊 RESUMEN DE EJECUCIÓN")
    logger.info("="*70)
    logger.info(f"Fecha: {resumen['fecha']}")
    logger.info(f"Total eventos: {resumen['total_eventos']}")
    logger.info(f"Datos recolectados: {resumen['total_datos_recolectados']}")
    logger.info(f"Modelos entrenados: {resumen['total_modelos_entrenados']}")
    logger.info(f"Predicciones: {resumen['total_predicciones']}")
    logger.info(f"Errores: {resumen['total_errores']}")
    logger.info(f"Duración: {resumen['duracion_minutos']:.1f} minutos")
    logger.info(f"Fuentes: {', '.join(resumen['fuentes_datos'])}")
    logger.info("="*70 + "\n")

    # Guardar
    log.save()
    log.exportar_csv()

    return resumen

# ============================================================================
# HISTORIAL DE ÚLTIMOS 30 DÍAS
# ============================================================================

def obtener_historial_ejecutiones(dias=30):
    """Obtiene historial de últimas ejecuciones"""
    log_dir = Path("logs")
    historial = []

    for i in range(dias):
        fecha = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        archivo = log_dir / f"ejecucion_{fecha}.json"

        if archivo.exists():
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    resumen = ExecutionLog().generar_resumen()
                    historial.append({
                        'fecha': fecha,
                        'archivo': str(archivo),
                        'eventos': len(data.get('eventos', [])),
                        'errores': len(data.get('errores', [])),
                        'predicciones': len(data.get('predicciones', []))
                    })
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo {archivo}: {e}")

    return historial

# ============================================================================
# TESTING
# ============================================================================

if __name__ == '__main__':
    log = log_ejecucion_diaria()

    # Simular ejecución
    log.registrar_datos_recolectados('Banco Central', 3, {'TC': 800, 'TPM': 6.5})
    log.registrar_datos_recolectados('bencinaenlinea.cl', 3, {'bencina_95': 1150, 'diesel': 1080})
    log.registrar_modelo_entrenado('ARIMA', {'mae': 0.35, 'rmse': 0.48})
    log.registrar_modelo_entrenado('XGBoost', {'mae': 0.32, 'rmse': 0.45})
    log.registrar_modelo_entrenado('LSTM', {'mae': 0.38, 'rmse': 0.50})
    log.registrar_prediccion('2026-08', 0.26, {'min': 0.1, 'max': 0.42})
    log.agregar_estadistica('temperatura_promedio', 18.5)

    log_resumen_final(log)

    print("\n📋 Historial de últimos 7 días:")
    historial = obtener_historial_ejecutiones(7)
    for registro in historial:
        print(f"  {registro['fecha']}: {registro['eventos']} eventos, {registro['errores']} errores")
