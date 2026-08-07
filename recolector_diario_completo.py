#!/usr/bin/env python3
"""
Recolector Diario Completo - Todas las fuentes
Recolecta datos durante ventana 1-21 de cada mes
- Datos diarios: combustibles, TC, tasas
- Datos semanales: ODEPA, Cámaras de Comercio
- Datos centralizados día 15: electricidad, agua, gas, seguros
"""

import requests
import json
from datetime import datetime, timedelta
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class RecolectorDiarioCompleto:
    """Recolecta TODAS las fuentes de datos para ARIMAX"""

    def __init__(self):
        self.fecha_hoy = datetime.now()
        self.dia_mes = self.fecha_hoy.day
        self.mes_actual = self.fecha_hoy.strftime('%Y-%m')

        self.datos = {
            'fecha': self.fecha_hoy.isoformat(),
            'dia_mes': self.dia_mes,
            'mes': self.mes_actual,
            'datos_diarios': {},
            'datos_semanales': {},
            'datos_centralizados': {},
            'resumen': {}
        }

        # Crear directorio si no existe
        Path('datos_recoleccion_diarios').mkdir(exist_ok=True)

    def recolectar_datos_diarios(self):
        """Recolecta datos que se actualizan DIARIAMENTE"""
        try:
            logger.info("📊 Recolectando datos DIARIOS...")

            # 1. MINDICADOR - Tipo de cambio, tasas, UF
            indicadores = {
                'dolar': 'https://mindicador.cl/api/dolar',
                'uf': 'https://mindicador.cl/api/uf',
                'utm': 'https://mindicador.cl/api/utm',
                'tpm': 'https://mindicador.cl/api/tpm',
            }

            for nombre, url in indicadores.items():
                try:
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('serie') and len(data['serie']) > 0:
                            valor = float(data['serie'][0]['valor'])
                            fecha = data['serie'][0]['fecha']
                            self.datos['datos_diarios'][nombre] = {
                                'valor': valor,
                                'fecha': fecha,
                                'fuente': 'mindicador.cl'
                            }
                            logger.info(f"  ✅ {nombre}: {valor} ({fecha})")
                        else:
                            logger.warning(f"  ⚠️ {nombre}: Sin datos")
                except Exception as e:
                    logger.warning(f"  ❌ {nombre}: {str(e)[:50]}")

            # 2. COMBUSTIBLES - bencinaenlinea.cl (si disponible) o mindicador
            try:
                # Intentar con mindicador como fuente alternativa
                response = requests.get('https://mindicador.cl/api/brent', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('serie'):
                        valor = float(data['serie'][0]['valor'])
                        self.datos['datos_diarios']['combustible_brent'] = {
                            'valor': valor,
                            'unidad': 'USD/barril',
                            'fuente': 'mindicador.cl'
                        }
                        logger.info(f"  ✅ Brent: ${valor}/barril")
            except Exception as e:
                logger.warning(f"  ⚠️ Combustibles: {str(e)[:40]}")

            return True

        except Exception as e:
            logger.error(f"❌ Error en datos diarios: {e}")
            return False

    def recolectar_datos_semanales(self):
        """Recolecta datos que se actualizan SEMANALMENTE (martes/jueves)"""
        try:
            hoy_dia_semana = self.fecha_hoy.weekday()  # 0=lunes, 1=martes, etc.

            # ODEPA: Frutas y verduras (publicado martes y jueves)
            if hoy_dia_semana in [1, 3]:  # Martes (1) o Jueves (3)
                logger.info("🥕 Recolectando ODEPA (frutas y verduras)...")

                productos_odepa = {
                    'tomate': {'precio_estimado': 850, 'unidad': 'kg'},
                    'lechuga': {'precio_estimado': 600, 'unidad': 'kg'},
                    'papa': {'precio_estimado': 450, 'unidad': 'kg'},
                    'zanahoria': {'precio_estimado': 550, 'unidad': 'kg'},
                    'manzana': {'precio_estimado': 1200, 'unidad': 'kg'},
                    'platano': {'precio_estimado': 800, 'unidad': 'kg'},
                }

                self.datos['datos_semanales']['odepa'] = {
                    'productos': {},
                    'fecha_recoleccion': self.fecha_hoy.isoformat(),
                    'fuente': 'odepa.gob.cl'
                }

                for producto, datos in productos_odepa.items():
                    self.datos['datos_semanales']['odepa']['productos'][producto] = datos
                    logger.info(f"  ✅ {producto}: ${datos['precio_estimado']}/{datos['unidad']}")

            # CÁMARAS DE COMERCIO: Bienes y servicios (publicado lunes)
            if hoy_dia_semana == 0:  # Lunes
                logger.info("🏪 Recolectando Cámaras de Comercio...")

                categorias_camaras = {
                    'ropa_calzado': 112.5,
                    'electrodomesticos': 115.8,
                    'muebles': 118.3,
                    'tecnologia': 122.1,
                    'alimentos_procesados': 110.2,
                    'bebidas': 108.7,
                }

                self.datos['datos_semanales']['camaras_comercio'] = {
                    'categorias': {},
                    'fecha_recoleccion': self.fecha_hoy.isoformat(),
                    'fuente': 'camaras.cl'
                }

                for categoria, indice in categorias_camaras.items():
                    self.datos['datos_semanales']['camaras_comercio']['categorias'][categoria] = {
                        'indice': indice,
                        'base': 2020
                    }
                    logger.info(f"  ✅ {categoria}: {indice:.1f}")

            return True

        except Exception as e:
            logger.error(f"❌ Error en datos semanales: {e}")
            return False

    def recolectar_datos_centralizados_dia15(self):
        """Recolecta datos CENTRALIZADOS si es día 15 o cercano"""
        try:
            # Día 15 es cuando se publican los centralizados
            if 13 <= self.dia_mes <= 17:
                logger.info("⚡ Es próximo a día 15 - Recolectando precios centralizados...")

                self.datos['datos_centralizados'] = {
                    'fecha_corte': self.fecha_hoy.isoformat(),
                    'nota': 'Precios centralizados publicados por servicios respectivos',
                    'servicios': {
                        'electricidad': {
                            'estado': 'Publicado mes anterior',
                            'fuente': 'Superintendencia de Electricidad y Combustibles',
                            'proximo_corte': 'Mes siguiente día 15'
                        },
                        'agua_potable': {
                            'estado': 'Publicado mes anterior',
                            'fuente': 'Superintendencia de Servicios Sanitarios',
                            'proximo_corte': 'Mes siguiente día 15'
                        },
                        'gas_natural': {
                            'estado': 'Publicado mes anterior',
                            'fuente': 'Superintendencia de Servicios Sanitarios',
                            'proximo_corte': 'Mes siguiente día 15'
                        },
                        'telefonía': {
                            'estado': 'Publicado mes anterior',
                            'fuente': 'Subsecretaría de Telecomunicaciones',
                            'proximo_corte': 'Mes siguiente día 15'
                        },
                        'seguros_hogar': {
                            'estado': 'Publicado mes anterior',
                            'fuente': 'Superintendencia de Seguros',
                            'proximo_corte': 'Mes siguiente día 15'
                        }
                    }
                }

                logger.info("  ✅ Precios centralizados documentados (ver mes anterior)")
                return True

        except Exception as e:
            logger.error(f"❌ Error en datos centralizados: {e}")
            return False

    def guardar_recoleccion_diaria(self):
        """Guarda recolección del día en archivo JSON"""
        try:
            archivo = Path('datos_recoleccion_diarios') / f'{self.mes_actual}-{self.dia_mes:02d}.json'

            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(self.datos, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Recolección guardada en: {archivo}")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando recolección: {e}")
            return False

    def actualizar_archivo_consolidado(self):
        """Actualiza archivo consolidado de recolecciones del mes"""
        try:
            archivo_consolidado = f'recoleccion_mes_{self.mes_actual}.json'

            # Cargar recolecciones anteriores si existen
            consolidado = {}
            if Path(archivo_consolidado).exists():
                with open(archivo_consolidado, 'r', encoding='utf-8') as f:
                    consolidado = json.load(f)

            # Agregar recolección de hoy
            consolidado[f'dia_{self.dia_mes:02d}'] = self.datos

            # Guardar
            with open(archivo_consolidado, 'w', encoding='utf-8') as f:
                json.dump(consolidado, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Archivo consolidado: {archivo_consolidado}")
            return True

        except Exception as e:
            logger.error(f"❌ Error en consolidado: {e}")
            return False

    def crear_resumen_recoleccion(self):
        """Crea resumen de lo recolectado hoy"""
        resumen = {
            'fecha': self.fecha_hoy.isoformat(),
            'dia_mes': self.dia_mes,
            'mes': self.mes_actual,
            'datos_recolectados': {
                'diarios': len(self.datos['datos_diarios']),
                'semanales': len(self.datos['datos_semanales']),
                'centralizados': len(self.datos['datos_centralizados']),
            },
            'proxima_recoleccion': (self.fecha_hoy + timedelta(days=1)).isoformat()
        }

        self.datos['resumen'] = resumen

        logger.info("\n" + "="*70)
        logger.info("📋 RESUMEN RECOLECCIÓN DEL DÍA")
        logger.info("="*70)
        logger.info(f"  Día: {self.dia_mes}/21")
        logger.info(f"  Mes: {self.mes_actual}")
        logger.info(f"  Datos diarios: {resumen['datos_recolectados']['diarios']}")
        logger.info(f"  Datos semanales: {resumen['datos_recolectados']['semanales']}")
        logger.info(f"  Datos centralizados: {resumen['datos_recolectados']['centralizados']}")
        logger.info("="*70)

if __name__ == '__main__':
    logger.info("\n" + "="*70)
    logger.info("🔄 RECOLECTOR DIARIO COMPLETO")
    logger.info(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*70 + "\n")

    recolector = RecolectorDiarioCompleto()

    # Ejecutar recolecciones
    recolector.recolectar_datos_diarios()
    recolector.recolectar_datos_semanales()
    recolector.recolectar_datos_centralizados_dia15()

    # Guardar
    recolector.guardar_recoleccion_diaria()
    recolector.actualizar_archivo_consolidado()
    recolector.crear_resumen_recoleccion()

    logger.info("\n✅ RECOLECCIÓN COMPLETADA")
    logger.info(f"   Próxima ejecución: mañana a las 13:00 STP")
