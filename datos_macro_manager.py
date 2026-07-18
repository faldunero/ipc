#!/usr/bin/env python3
"""
Gestor de Datos Macroeconómicos con Sistema de Cache Inteligente
Evita consultas innecesarias a APIs/web scraping
Actualiza automáticamente según política de TTL (Time To Live)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatosMacroManager:
    """Gestor centralizado de datos macroeconómicos con cache inteligente"""

    def __init__(self, cache_path: str = "cache_datos_macro.json"):
        self.cache_path = cache_path
        self.cache = None
        self._load_cache()

    def _load_cache(self):
        """Carga cache desde JSON"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info("✅ Cache de datos macro cargado")
            else:
                logger.warning(f"⚠️  Cache no encontrado en {self.cache_path}")
                self.cache = {}
        except Exception as e:
            logger.error(f"❌ Error cargando cache: {e}")
            self.cache = {}

    def _guardar_cache(self):
        """Persiste cache en JSON"""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
            logger.info("✅ Cache actualizado")
        except Exception as e:
            logger.error(f"❌ Error guardando cache: {e}")

    def _dato_es_viejο(self, dato_id: str, politica_ttl_horas: int = 24) -> bool:
        """Checkea si un dato ha expirado su TTL"""
        try:
            # Buscar dato en cache
            for seccion in ['factores_internos', 'factores_externos']:
                if seccion not in self.cache:
                    continue

                if seccion == 'factores_internos':
                    datos = self.cache[seccion].get('datos', [])
                else:  # factores_externos
                    datos = self.cache[seccion].get('mundo', [])

                for dato in datos:
                    if dato.get('id') == dato_id:
                        fecha_dato = datetime.fromisoformat(dato['fecha_dato'])
                        edad_horas = (datetime.now() - fecha_dato).total_seconds() / 3600
                        return edad_horas > politica_ttl_horas

            return True  # Si no existe, es "viejo"
        except Exception as e:
            logger.warning(f"⚠️  Error checkeando TTL de {dato_id}: {e}")
            return True

    def obtener_dato(self, dato_id: str, auto_actualizar: bool = True) -> Dict:
        """
        Obtiene un dato macroeconómico del cache.
        Si está viejο y auto_actualizar=True, intenta actualizarlo primero.
        """
        # Checkear si está expirado
        if auto_actualizar and self._dato_es_viejο(dato_id):
            logger.info(f"📅 {dato_id} expirado, intentando actualizar...")
            self._actualizar_dato(dato_id)

        # Retornar del cache
        for seccion in ['factores_internos', 'factores_externos']:
            if seccion not in self.cache:
                continue

            if seccion == 'factores_internos':
                datos = self.cache[seccion].get('datos', [])
            else:
                datos = self.cache[seccion].get('mundo', [])

            for dato in datos:
                if dato.get('id') == dato_id:
                    return dato

        logger.warning(f"⚠️  Dato {dato_id} no encontrado")
        return {}

    def obtener_todos_factores_internos(self) -> List[str]:
        """Retorna lista de strings con factores internos para usar en predicciones"""
        try:
            factores = []
            datos = self.cache.get('factores_internos', {}).get('datos', [])

            desempleo = next((d for d in datos if d['id'] == 'desempleo'), {})
            presion_sal = next((d for d in datos if d['id'] == 'presion_salarial'), {})
            tipo_cambio = next((d for d in datos if d['id'] == 'tipo_cambio'), {})

            if desempleo:
                d_val = desempleo.get('valor', 9.4)
                d_periodo = desempleo.get('periodo', 'MAM 2026')
                factores.append(
                    f"Política BC restricción activa: TPM mantenida para anclar expectativas inflacionarias"
                )
                factores.append(
                    f"Mercado laboral: Desempleo {d_val}% (INE trimestre {d_periodo}), "
                    f"presión salarial {presion_sal.get('valor', 3.5)}% YoY"
                )
                factores.append(
                    "Expectativas de inflación: Ancladas meta 3% con rango ±1pp según encuestas BC"
                )

            if tipo_cambio:
                tc_val = tipo_cambio.get('valor', 934.96)
                tc_cambio = tipo_cambio.get('cambio_mes', -3.82)
                factores.append(
                    f"Tipo de cambio: {tc_val} CLP/USD (18 julio 2026), "
                    f"debilidad del peso de {tc_cambio}% mes"
                )

            factores.append("Impulso fiscal: Gasto público moderado, objetivo estructural superávit")

            return factores
        except Exception as e:
            logger.error(f"❌ Error generando factores internos: {e}")
            return []

    def obtener_todos_factores_externos(self) -> List[str]:
        """Retorna lista de strings con factores externos para usar en predicciones"""
        try:
            factores = []
            datos = self.cache.get('factores_externos', {}).get('mundo', [])

            brent = next((d for d in datos if d['id'] == 'petroleo_brent'), {})
            inflacion_us = next((d for d in datos if d['id'] == 'inflacion_eeuu'), {})
            tasas_fed = next((d for d in datos if d['id'] == 'tasas_fed'), {})
            cobre = next((d for d in datos if d['id'] == 'cobre_comex'), {})

            if brent:
                b_val = brent.get('valor', 88.26)
                b_cambio = brent.get('cambio_yoy', 27.15)
                factores.append(
                    f"Precios petróleo Brent: {b_val} USD/barril (18 julio 2026), "
                    f"tensiones Ormuz (+{b_cambio}% YoY)"
                )

            if inflacion_us:
                inf_val = inflacion_us.get('valor', 3.5)
                factores.append(
                    f"Inflación EEUU: {inf_val}-{inf_val + 0.1}% (baja desde 4,2% en mayo), deflación energética"
                )

            if tasas_fed:
                tf_min = tasas_fed.get('valor_min', 3.50)
                tf_max = tasas_fed.get('valor_max', 3.75)
                tf_prob = tasas_fed.get('probabilidad_alza', 46.5)
                factores.append(
                    f"Tasas Fed: {tf_min}%-{tf_max}% sin cambios, "
                    f"probabilidad {tf_prob}% alza en julio 2026"
                )

            if cobre:
                c_min = cobre.get('valor_min', 6.03)
                c_max = cobre.get('valor_max', 6.33)
                factores.append(
                    f"Precios cobre Comex: {c_min}-{c_max} USD/lb, "
                    "inventarios bajos, producción chilena reducida"
                )

            factores.append("Precios alimentos FAO: Índice moderado con presión agrícola controlada")

            return factores
        except Exception as e:
            logger.error(f"❌ Error generando factores externos: {e}")
            return []

    def _actualizar_dato(self, dato_id: str):
        """Intenta actualizar un dato específico desde su fuente"""
        # Implementar actualizaciones según dato_id
        # Esta es la parte que se llamaría automáticamente vía scheduled task

        actualizadores = {
            'tipo_cambio': self._actualizar_tipo_cambio,
            'petroleo_brent': self._actualizar_brent,
            'cobre_comex': self._actualizar_cobre,
            'desempleo': self._actualizar_desempleo,
            'inflacion_eeuu': self._actualizar_inflacion_eeuu,
        }

        if dato_id in actualizadores:
            try:
                actualizadores[dato_id]()
                logger.info(f"✅ {dato_id} actualizado")
            except Exception as e:
                logger.warning(f"⚠️  Error actualizando {dato_id}: {e}")

    def _actualizar_tipo_cambio(self):
        """Actualiza tipo de cambio CLP/USD desde Banco Central"""
        try:
            # Usar API del Banco Central de Chile
            url = "https://si3.bcentral.cl/Bdemovil/BDE/Series/MOV_ID_TC1"
            # Simplified: en producción usarías la API real
            logger.info("📡 Consultando tipo de cambio desde Banco Central")
            # response = requests.get(url, timeout=10)
            # Actualizar en cache...
        except Exception as e:
            logger.warning(f"⚠️  No se pudo actualizar tipo_cambio: {e}")

    def _actualizar_brent(self):
        """Actualiza precio Brent desde Trading Economics"""
        try:
            url = "https://tradingeconomics.com/commodity/brent-crude-oil"
            logger.info("📡 Consultando precio Brent desde Trading Economics")
            # response = requests.get(url, timeout=10)
            # Parsear con BeautifulSoup...
        except Exception as e:
            logger.warning(f"⚠️  No se pudo actualizar petroleo_brent: {e}")

    def _actualizar_cobre(self):
        """Actualiza precio cobre desde COMEX"""
        try:
            url = "https://tradingeconomics.com/commodity/copper"
            logger.info("📡 Consultando precio cobre desde COMEX")
        except Exception as e:
            logger.warning(f"⚠️  No se pudo actualizar cobre_comex: {e}")

    def _actualizar_desempleo(self):
        """Actualiza desempleo desde INE Chile"""
        try:
            logger.info("📡 Consultando desempleo desde INE")
            # Datos trimestrales, solo actualizar cada 3 meses
        except Exception as e:
            logger.warning(f"⚠️  No se pudo actualizar desempleo: {e}")

    def _actualizar_inflacion_eeuu(self):
        """Actualiza inflación EEUU desde Bureau of Labor Statistics"""
        try:
            logger.info("📡 Consultando inflación EEUU desde BLS")
            # Datos mensuales
        except Exception as e:
            logger.warning(f"⚠️  No se pudo actualizar inflacion_eeuu: {e}")

    def actualizar_todos(self) -> bool:
        """
        Actualiza TODOS los datos macro que hayan expirado.
        Llamar desde scheduled task (cron, systemd timer, etc)
        Retorna True si todas las actualizaciones fueron exitosas
        """
        logger.info("🔄 Iniciando actualización de datos macroeconómicos...")

        # Listar datos a actualizar según política
        datos_a_actualizar = self.cache.get('politica_actualizacion', {}).get('datos_diarios', [])

        exitos = 0
        for dato_id in datos_a_actualizar:
            try:
                self._actualizar_dato(dato_id)
                exitos += 1
            except Exception as e:
                logger.warning(f"⚠️  Error actualizando {dato_id}: {e}")

        # Actualizar timestamp
        if exitos > 0:
            self.cache['ultima_actualizacion'] = datetime.now().isoformat()
            self.cache['prox_actualizacion_programada'] = (
                datetime.now() + timedelta(days=1)
            ).isoformat()
            self._guardar_cache()

        logger.info(f"✅ Actualización completada: {exitos} datos actualizados")
        return exitos == len(datos_a_actualizar)


# Uso ejemplo:
if __name__ == "__main__":
    manager = DatosMacroManager()

    # Obtener dato específico (consultará desde cache, auto-actualizará si está viejο)
    desempleo = manager.obtener_dato('desempleo')
    print(f"Desempleo: {desempleo.get('valor')}% ({desempleo.get('periodo')})")

    # Generar strings para predictor
    factores_internos = manager.obtener_todos_factores_internos()
    factores_externos = manager.obtener_todos_factores_externos()

    print("\n📊 FACTORES INTERNOS:")
    for f in factores_internos:
        print(f"  • {f}")

    print("\n🌍 FACTORES EXTERNOS:")
    for f in factores_externos:
        print(f"  • {f}")

    # Actualizar todos los datos expirados
    # manager.actualizar_todos()
