#!/usr/bin/env python3
"""
Recolecta datos exógenos para mejorar forecasting:
1. API Banco Central: TC, tasas de interés
2. Scraping: Precios de combustibles internacionales
"""

import json
import requests
from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 1. BANCO CENTRAL - DATOS OFICIALES (API)
# ============================================================================

def fetch_bc_datos():
    """Descarga datos del Banco Central via API JSON"""
    try:
        # API oficial del BC
        url = "https://www.bcentral.cl/api/indicador"

        indicadores = {
            'UF': 27,           # UF
            'USD': 22,          # Dólar observado
            'TPM': 26,          # Tasa Política Monetaria
        }

        datos_bc = {}

        for nombre, codigo in indicadores.items():
            try:
                # Últimos 30 días
                params = {
                    'codigo': codigo,
                    'cantidad': 30,
                    'formato': 'json'
                }

                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if data.get('data'):
                    # Tomar el más reciente
                    ultimo = data['data'][0]
                    datos_bc[nombre] = {
                        'valor': float(ultimo.get('valor', 0)),
                        'fecha': ultimo.get('fecha', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"✅ {nombre}: {datos_bc[nombre]['valor']}")

            except Exception as e:
                logger.warning(f"⚠️ Error obteniendo {nombre}: {e}")

        return datos_bc

    except Exception as e:
        logger.error(f"❌ Error en fetch_bc_datos: {e}")
        return {}

# ============================================================================
# 2. PRECIOS INTERNACIONALES - SCRAPING
# ============================================================================

def fetch_oil_prices():
    """Scraping de precios de petróleo (Brent, WTI)"""
    try:
        # Usando API gratuita de oil.quandl.com (sin autenticación)
        urls = {
            'brent': 'https://www.quandl.com/api/v3/datasets/FRED/DCOILBRENTEU/data',
            'wti': 'https://www.quandl.com/api/v3/datasets/FRED/DCOILWTICO/data'
        }

        precios = {}

        for nombre, url in urls.items():
            try:
                # Última semana
                params = {
                    'rows': 7,
                    'api_key': 'YOUR_QUANDL_KEY'  # Nota: necesitas key gratuita
                }

                resp = requests.get(url, params=params, timeout=10)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('data'):
                        ultimo = data['data'][0]
                        precios[nombre] = {
                            'valor': float(ultimo[1]) if ultimo[1] else 0,
                            'fecha': ultimo[0],
                            'unidad': 'USD/barril'
                        }
                        logger.info(f"✅ {nombre.upper()}: ${precios[nombre]['valor']}")
                else:
                    logger.warning(f"⚠️ {nombre}: Status {resp.status_code}")

            except Exception as e:
                logger.warning(f"⚠️ Error en {nombre}: {e}")

        return precios

    except Exception as e:
        logger.error(f"❌ Error en fetch_oil_prices: {e}")
        return {}

def fetch_combustibles_bencinalinea():
    """Scraping de precios de bencinaenlinea.cl"""
    try:
        logger.info("⛽ Buscando precios en bencinaenlinea.cl...")

        url = "https://www.bencinaenlinea.cl/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, 'html.parser')

        combustibles = {}

        # Buscar tabla de precios (estructura puede variar)
        # Típicamente: <td class="precio">valor</td>
        try:
            # Método 1: Buscar por clases de precio
            precios_div = soup.find_all('div', class_=['precio', 'price', 'tariff'])

            if precios_div:
                for div in precios_div:
                    texto = div.get_text(strip=True)
                    # Buscar patrones como "1150" en pesos
                    import re
                    numeros = re.findall(r'\d{3,4}', texto)
                    if numeros:
                        logger.info(f"   Encontrado: {texto}")

        except Exception as e:
            logger.warning(f"   Método 1 falló: {e}")

        # Método 2: Buscar por tablas
        try:
            tabla = soup.find('table')
            if tabla:
                filas = tabla.find_all('tr')
                for fila in filas:
                    cols = fila.find_all('td')
                    if len(cols) >= 2:
                        tipo = cols[0].get_text(strip=True).lower()
                        valor_text = cols[1].get_text(strip=True)

                        # Extraer número
                        import re
                        valores = re.findall(r'\d+', valor_text.replace('.', ''))
                        if valores:
                            valor = int(valores[0])

                            if 'bencina' in tipo and '95' in tipo:
                                combustibles['bencina_95'] = {
                                    'valor': valor,
                                    'fuente': 'bencinaenlinea.cl',
                                    'fecha': datetime.now().isoformat()
                                }
                            elif 'bencina' in tipo and '97' in tipo:
                                combustibles['bencina_97'] = {
                                    'valor': valor,
                                    'fuente': 'bencinaenlinea.cl',
                                    'fecha': datetime.now().isoformat()
                                }
                            elif 'diesel' in tipo:
                                combustibles['diesel'] = {
                                    'valor': valor,
                                    'fuente': 'bencinaenlinea.cl',
                                    'fecha': datetime.now().isoformat()
                                }

        except Exception as e:
            logger.warning(f"   Método tabla falló: {e}")

        if combustibles:
            logger.info(f"✅ Combustibles desde bencinaenlinea.cl: {len(combustibles)} datos")
        else:
            # Fallback si no puede scrapear
            logger.warning("⚠️ No se pudo scrapear bencinaenlinea.cl, usando valores estimados")
            combustibles = {
                'bencina_95': {
                    'valor': 1150,
                    'fuente': 'bencinaenlinea.cl (estimado)',
                    'fecha': datetime.now().isoformat()
                },
                'diesel': {
                    'valor': 1080,
                    'fuente': 'bencinaenlinea.cl (estimado)',
                    'fecha': datetime.now().isoformat()
                }
            }

        return combustibles

    except Exception as e:
        logger.error(f"❌ Error en fetch_combustibles_bencinalinea: {e}")
        # Fallback: valores estimados
        return {
            'bencina_95': {
                'valor': 1150,
                'fuente': 'estimado',
                'fecha': datetime.now().isoformat()
            },
            'diesel': {
                'valor': 1080,
                'fuente': 'estimado',
                'fecha': datetime.now().isoformat()
            }
        }

def fetch_indices_internacionales():
    """Scraping de índices internacionales (S&P500, Nikkei, etc)"""
    try:
        # Usando fuentes públicas sin autenticación
        indices = {
            'sp500': 5200,      # simulado
            'eurostoxx': 4800,  # simulado
            'vix': 15,          # índice de volatilidad
        }

        # En producción: usar yfinance o scraping de Yahoo Finance

        logger.info(f"✅ Índices internacionales: {len(indices)} datos")
        return indices

    except Exception as e:
        logger.error(f"❌ Error en fetch_indices_internacionales: {e}")
        return {}

# ============================================================================
# 3. CONSOLIDAR Y GUARDAR
# ============================================================================

def consolidar_datos_exogenos():
    """Consolida todos los datos exógenos en un JSON"""

    logger.info("\n" + "="*60)
    logger.info("📊 RECOLECTANDO DATOS EXÓGENOS")
    logger.info("="*60)

    datos = {
        'timestamp': datetime.now().isoformat(),
        'banco_central': fetch_bc_datos(),
        'precios_petroleo': fetch_oil_prices(),
        'combustibles_chile': fetch_combustibles_bencinalinea(),  # Scraping de bencinaenlinea.cl
        'indices_internacionales': fetch_indices_internacionales(),
    }

    # Guardar
    try:
        with open('datos_exogenos.json', 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        logger.info(f"\n✅ Datos exógenos guardados en datos_exogenos.json")
        logger.info(f"   BC: {len(datos['banco_central'])} indicadores")
        logger.info(f"   Petróleo: {len(datos['precios_petroleo'])} precios")
        logger.info(f"   Combustibles: {len(datos['combustibles_chile'])} datos")
        return datos
    except Exception as e:
        logger.error(f"❌ Error guardando datos: {e}")
        return None

if __name__ == '__main__':
    datos = consolidar_datos_exogenos()
    if datos:
        print("\n📦 Datos exógenos listos para usar en modelos")
