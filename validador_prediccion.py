#!/usr/bin/env python3
"""
Validador de Predicciones - Compara predicción vs IPC real del INE
Ejecutar DESPUÉS de que INE publica el IPC (día 8 del mes siguiente)
- Carga predicción que se hizo días 1-21 del mes anterior
- Compara con IPC real publicado por INE
- Calcula métricas: MAE, RMSE, error %
- Guarda historial de validaciones
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class ValidadorPrediccion:
    """Valida predicciones contra valor real del INE"""

    def __init__(self):
        self.fecha_hoy = datetime.now()
        self.prediccion_actual = None
        self.ipc_real = None
        self.error = None
        self.metricas = {}

    def calcular_fecha_publicacion_ine(self, mes_referencia):
        """
        Calcula fecha de publicación del IPC del mes de referencia
        INE publica el día 8 o día hábil ANTERIOR si el 8 no es hábil
        """
        # Parsear mes (YYYY-MM)
        año, mes = map(int, mes_referencia.split('-'))

        # Día 8 del mes siguiente
        if mes == 12:
            fecha_publicacion = datetime(año + 1, 1, 8)
        else:
            fecha_publicacion = datetime(año, mes + 1, 8)

        # Si no es día hábil (sábado=5, domingo=6), retroceder al viernes anterior
        dias_retroceso = 0
        while fecha_publicacion.weekday() >= 5:  # 5=sábado, 6=domingo
            fecha_publicacion -= timedelta(days=1)
            dias_retroceso += 1

        if dias_retroceso > 0:
            logger.info(f"   Día 8 no es hábil, publicación retrocedida: {fecha_publicacion.strftime('%Y-%m-%d (%A)')}")
        else:
            logger.info(f"   Publicación día 8 (hábil): {fecha_publicacion.strftime('%Y-%m-%d (%A)')}")

        return fecha_publicacion

    def cargar_prediccion_anterior(self, mes_predicho):
        """Carga la predicción que se hizo para el mes anterior"""
        try:
            logger.info(f"📂 Buscando predicción para mes: {mes_predicho}...")

            archivo_prediccion = 'prediccion_actual.json'

            if Path(archivo_prediccion).exists():
                with open(archivo_prediccion, 'r', encoding='utf-8') as f:
                    self.prediccion_actual = json.load(f)

                logger.info(f"✅ Predicción cargada:")
                logger.info(f"   Predicción: {self.prediccion_actual['prediccion']}%")
                logger.info(f"   IC: [{self.prediccion_actual['intervalo_confianza']['min']:.4f}%, {self.prediccion_actual['intervalo_confianza']['max']:.4f}%]")
                logger.info(f"   Confianza: {self.prediccion_actual['nivel_confianza']}")
                return True
            else:
                logger.error(f"❌ No encontrada predicción en {archivo_prediccion}")
                return False

        except Exception as e:
            logger.error(f"❌ Error cargando predicción: {e}")
            return False

    def cargar_ipc_real_ine(self, mes_predicho, valor_real=None):
        """
        Carga IPC real publicado por INE
        En producción, se integraría con API del INE o se ingresa manualmente
        """
        try:
            logger.info(f"📊 Cargando IPC real del INE para: {mes_predicho}...")

            # Verificar si ya se publicó
            fecha_publicacion = self.calcular_fecha_publicacion_ine(mes_predicho)
            if self.fecha_hoy < fecha_publicacion:
                logger.warning(f"⚠️ INE aún no publica este IPC")
                logger.info(f"   Se publicará: {fecha_publicacion.strftime('%Y-%m-%d (%A)')}")
                logger.info(f"   Faltan: {(fecha_publicacion - self.fecha_hoy).days} días")
                return False

            # Opción 1: Si se pasa valor real como parámetro
            if valor_real is not None:
                self.ipc_real = valor_real
                logger.info(f"✅ IPC real ingresado: {valor_real}%")
                return True

            # Opción 2: Buscar en archivo local de registros del INE
            archivo_ine = 'ipc_real_ine.json'
            if Path(archivo_ine).exists():
                with open(archivo_ine, 'r', encoding='utf-8') as f:
                    datos_ine = json.load(f)

                if mes_predicho in datos_ine:
                    self.ipc_real = float(datos_ine[mes_predicho])
                    logger.info(f"✅ IPC real cargado desde registro: {self.ipc_real}%")
                    return True

            logger.error(f"❌ IPC real no disponible para {mes_predicho}")
            logger.info(f"   Para validar, ingresa manualmente:")
            logger.info(f"   python3 validador_prediccion.py --mes {mes_predicho} --real 0.15")
            return False

        except Exception as e:
            logger.error(f"❌ Error cargando IPC real: {e}")
            return False

    def calcular_metricas(self):
        """Calcula métricas de error"""
        try:
            if not self.prediccion_actual or self.ipc_real is None:
                logger.error("❌ No hay predicción o IPC real para comparar")
                return False

            pred = self.prediccion_actual['prediccion']
            real = self.ipc_real

            # Error absoluto
            error_abs = abs(pred - real)

            # Error porcentual
            error_pct = (error_abs / real * 100) if real != 0 else 0

            # Acierto direccional (si ambos suben o ambos bajan)
            acierto_direccional = (pred >= 0 and real >= 0) or (pred < 0 and real < 0)

            # Dentro de IC?
            ic_min = self.prediccion_actual['intervalo_confianza']['min']
            ic_max = self.prediccion_actual['intervalo_confianza']['max']
            dentro_ic = ic_min <= real <= ic_max

            self.metricas = {
                'prediccion': pred,
                'real': real,
                'error_absoluto': error_abs,
                'error_porcentual': error_pct,
                'acierto_direccional': acierto_direccional,
                'dentro_intervalo_confianza': dentro_ic,
                'intervalo_confianza': {
                    'min': ic_min,
                    'max': ic_max
                },
                'completitud_recoleccion': self.prediccion_actual.get('completitud_recoleccion', 'N/A'),
                'nivel_confianza': self.prediccion_actual.get('nivel_confianza', 'N/A'),
                'timestamp_validacion': datetime.now().isoformat()
            }

            logger.info("\n" + "="*70)
            logger.info("📊 MÉTRICAS DE VALIDACIÓN")
            logger.info("="*70)
            logger.info(f"  Predicción: {pred:.4f}%")
            logger.info(f"  Valor Real: {real:.4f}%")
            logger.info(f"  Error Absoluto: {error_abs:.4f}%")
            logger.info(f"  Error Porcentual: {error_pct:.2f}%")
            logger.info(f"  Acierto Direccional: {'✅ SÍ' if acierto_direccional else '❌ NO'}")
            logger.info(f"  Dentro de IC: {'✅ SÍ' if dentro_ic else '❌ NO'}")
            logger.info(f"  IC: [{ic_min:.4f}%, {ic_max:.4f}%]")
            logger.info(f"  Completitud recolección: {self.prediccion_actual.get('completitud_recoleccion', 'N/A')}")
            logger.info(f"  Nivel de confianza: {self.prediccion_actual.get('nivel_confianza', 'N/A')}")
            logger.info("="*70)

            return True

        except Exception as e:
            logger.error(f"❌ Error calculando métricas: {e}")
            return False

    def guardar_validacion(self, mes_validado):
        """Guarda registro de validación en histórico"""
        try:
            archivo_historico = 'historico_validaciones.json'

            # Cargar histórico anterior
            historico = {}
            if Path(archivo_historico).exists():
                with open(archivo_historico, 'r', encoding='utf-8') as f:
                    historico = json.load(f)

            # Agregar validación de hoy
            historico[mes_validado] = self.metricas

            # Guardar
            with open(archivo_historico, 'w', encoding='utf-8') as f:
                json.dump(historico, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Validación guardada en: {archivo_historico}")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando validación: {e}")
            return False

    def calcular_estadisticas_acumuladas(self):
        """Calcula estadísticas de todo el histórico de validaciones"""
        try:
            archivo_historico = 'historico_validaciones.json'

            if not Path(archivo_historico).exists():
                logger.warning("⚠️ No hay histórico de validaciones todavía")
                return None

            with open(archivo_historico, 'r', encoding='utf-8') as f:
                historico = json.load(f)

            if not historico:
                return None

            # Calcular MAE, RMSE, % acierto direccional
            errores = [abs(v['error_absoluto']) for v in historico.values()]
            aciertos_dir = sum([1 for v in historico.values() if v['acierto_direccional']])
            dentro_ic = sum([1 for v in historico.values() if v['dentro_intervalo_confianza']])

            mae = np.mean(errores)
            rmse = np.sqrt(np.mean(np.array(errores)**2))
            pct_acierto_dir = (aciertos_dir / len(historico)) * 100
            pct_dentro_ic = (dentro_ic / len(historico)) * 100

            estadisticas = {
                'meses_validados': len(historico),
                'mae': float(mae),
                'rmse': float(rmse),
                'acierto_direccional_pct': float(pct_acierto_dir),
                'predicciones_dentro_ic_pct': float(pct_dentro_ic),
                'timestamp': datetime.now().isoformat()
            }

            logger.info("\n" + "="*70)
            logger.info("📈 ESTADÍSTICAS ACUMULADAS")
            logger.info("="*70)
            logger.info(f"  Meses validados: {estadisticas['meses_validados']}")
            logger.info(f"  MAE: {estadisticas['mae']:.4f}%")
            logger.info(f"  RMSE: {estadisticas['rmse']:.4f}%")
            logger.info(f"  Acierto Direccional: {estadisticas['acierto_direccional_pct']:.1f}%")
            logger.info(f"  Predicciones dentro de IC: {estadisticas['predicciones_dentro_ic_pct']:.1f}%")
            logger.info("="*70)

            return estadisticas

        except Exception as e:
            logger.error(f"❌ Error calculando estadísticas: {e}")
            return None

if __name__ == '__main__':
    import sys

    logger.info("\n" + "="*70)
    logger.info("✅ VALIDADOR DE PREDICCIONES IPC")
    logger.info(f"   Fecha: {datetime.now().strftime('%Y-%m-%d')}")
    logger.info("="*70 + "\n")

    # Parsear argumentos
    mes_validar = None
    ipc_real = None

    if '--mes' in sys.argv:
        idx = sys.argv.index('--mes')
        mes_validar = sys.argv[idx + 1]

    if '--real' in sys.argv:
        idx = sys.argv.index('--real')
        ipc_real = float(sys.argv[idx + 1])

    # Si no se especifica mes, asumir mes anterior
    if not mes_validar:
        fecha_anterior = datetime.now() - timedelta(days=8)
        mes_validar = fecha_anterior.strftime('%Y-%m')

    logger.info(f"📅 Validando predicción para mes: {mes_validar}\n")

    validador = ValidadorPrediccion()

    # Cargar predicción
    if not validador.cargar_prediccion_anterior(mes_validar):
        logger.error("❌ No se pudo cargar predicción")
        exit(1)

    # Cargar IPC real
    if not validador.cargar_ipc_real_ine(mes_validar, ipc_real):
        logger.error("❌ No se pudo cargar IPC real")
        logger.info("\nUSO:")
        logger.info(f"  python3 validador_prediccion.py --mes {mes_validar} --real 0.15")
        exit(1)

    # Calcular métricas
    if not validador.calcular_metricas():
        logger.error("❌ Error en cálculo de métricas")
        exit(1)

    # Guardar validación
    if not validador.guardar_validacion(mes_validar):
        logger.error("⚠️ Error guardando validación (pero métricas calculadas)")

    # Mostrar estadísticas acumuladas
    estadisticas = validador.calcular_estadisticas_acumuladas()

    logger.info("\n✅ VALIDACIÓN COMPLETADA")
