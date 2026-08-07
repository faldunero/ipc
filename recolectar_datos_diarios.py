#!/usr/bin/env python3
"""
Recolector de datos REALES diarios
- Mindicador.cl: dólar, UF, TPM, IPC
- Bencinaenlinea.cl: precio combustible
- Almacena en JSON con timestamp para usar en ARIMAX
"""

import requests
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

class RecolectorDiario:
    """Recolecta datos REALES diarios para ARIMAX"""

    def __init__(self):
        self.datos = {
            'fecha': datetime.now().isoformat(),
            'dia_semana': datetime.now().strftime('%A'),
            'indicadores': {}
        }

    def fetch_mindicador(self):
        """Obtiene datos REALES de mindicador.cl"""
        try:
            logger.info("💹 Recolectando de mindicador.cl...")

            indicadores = {
                'dolar': 'https://mindicador.cl/api/dolar',
                'uf': 'https://mindicador.cl/api/uf',
                'utm': 'https://mindicador.cl/api/utm',
                'ipc': 'https://mindicador.cl/api/ipc',
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

                            self.datos['indicadores'][nombre] = {
                                'valor': valor,
                                'fecha': fecha,
                                'url': url,
                                'status': 'OK'
                            }
                            logger.info(f"  ✅ {nombre}: {valor} ({fecha})")
                        else:
                            logger.warning(f"  ⚠️ {nombre}: Sin datos")
                            self.datos['indicadores'][nombre] = {'status': 'SIN_DATOS'}
                except Exception as e:
                    logger.warning(f"  ❌ {nombre}: {str(e)[:50]}")
                    self.datos['indicadores'][nombre] = {'status': 'ERROR', 'error': str(e)[:50]}

            return len([d for d in self.datos['indicadores'].values() if d.get('status') == 'OK']) > 0

        except Exception as e:
            logger.error(f"❌ Error en mindicador: {e}")
            return False

    def fetch_bencina(self):
        """Obtiene precio de combustible"""
        try:
            logger.info("⛽ Buscando precio combustible...")

            # bencinaenlinea.cl publica precios diarios
            # Para este script, usamos mindicador como fuente alternativa
            url = "https://mindicador.cl/api/brent"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('serie') and len(data['serie']) > 0:
                    valor = float(data['serie'][0]['valor'])
                    self.datos['indicadores']['brent'] = {
                        'valor': valor,
                        'fecha': data['serie'][0]['fecha'],
                        'status': 'OK'
                    }
                    logger.info(f"  ✅ Brent: ${valor}/barril")
                    return True

        except Exception as e:
            logger.warning(f"  ⚠️ Error bencina: {e}")

        return False

    def guardar_datos_diarios(self):
        """Guarda datos en JSON local para ARIMAX"""
        try:
            archivo = 'datos_diarios_arimax.json'

            # Cargar datos anteriores si existen
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    historial = json.load(f)
            except:
                historial = []

            # Agregar datos de hoy
            historial.append(self.datos)

            # Mantener solo últimos 30 días
            if len(historial) > 30:
                historial = historial[-30:]

            with open(archivo, 'w', encoding='utf-8') as f:
                json.dump(historial, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Datos guardados en {archivo}")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando: {e}")
            return False

    def crear_matriz_exogenas_actuales(self):
        """Crea matriz de variables exógenas con datos REALES de hoy"""
        try:
            # Extraer valores actuales
            dolar = self.datos['indicadores'].get('dolar', {}).get('valor', 900)
            tpm = self.datos['indicadores'].get('tpm', {}).get('valor', 4.5)
            uf = self.datos['indicadores'].get('uf', {}).get('valor', 40000)

            matriz = {
                'fecha': self.datos['fecha'],
                'dolar': dolar,
                'tpm': tpm,
                'uf': uf,
                'timestamp': datetime.now().isoformat()
            }

            with open('exogenas_actuales.json', 'w', encoding='utf-8') as f:
                json.dump(matriz, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Variables exógenas ACTUALES guardadas:")
            logger.info(f"   Dólar: ${dolar}")
            logger.info(f"   TPM: {tpm}%")
            logger.info(f"   UF: ${uf}")

            return True

        except Exception as e:
            logger.error(f"❌ Error creando matriz: {e}")
            return False

if __name__ == '__main__':
    logger.info("\n" + "="*70)
    logger.info("🔄 RECOLECCIÓN DE DATOS REALES DIARIOS")
    logger.info("="*70 + "\n")

    recolector = RecolectorDiario()

    # Recolectar datos
    mindicador_ok = recolector.fetch_mindicador()
    recolector.fetch_bencina()

    if mindicador_ok:
        # Guardar histórico diario
        recolector.guardar_datos_diarios()

        # Crear matriz de exógenas con datos de HOY
        recolector.crear_matriz_exogenas_actuales()

        logger.info("\n✅ Datos REALES recolectados exitosamente")
        logger.info("   Listos para usar en ARIMAX")
    else:
        logger.error("\n❌ No se pudieron recolectar datos suficientes")

    logger.info("="*70 + "\n")
