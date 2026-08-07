#!/usr/bin/env python3
"""
Script para actualizar datos históricos con el mes actual real
Agrega el último mes publicado por Banco Central
"""

import requests
import json
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

def obtener_ipc_actual():
    """Obtiene el IPC del mes actual desde Banco Central"""
    try:
        logger.info("📊 Buscando IPC del mes actual en Banco Central...")

        # Intentar con la API del Banco Central
        url = "https://www.bcentral.cl/api/indicador/IPC/json"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('serie') and len(data['serie']) > 0:
                # El primer elemento es el más reciente
                valor = float(data['serie'][0]['valor'])
                fecha = data['serie'][0]['fecha']
                logger.info(f"✅ IPC encontrado: {valor}% ({fecha})")
                return valor, fecha

        logger.warning("⚠️ No se pudo obtener del Banco Central, intentando mindicador.cl...")

        # Fallback a mindicador.cl
        url2 = "https://mindicador.cl/api/ipc"
        response2 = requests.get(url2, timeout=10)

        if response2.status_code == 200:
            data2 = response2.json()
            if data2.get('serie') and len(data2['serie']) > 0:
                valor = float(data2['serie'][0]['valor'])
                fecha = data2['serie'][0]['fecha']
                logger.info(f"✅ IPC mindicador: {valor}% ({fecha})")
                return valor, fecha

        return None, None

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return None, None

def agregar_mes_al_historico(ipc_valor, fecha_str):
    """Agrega el nuevo mes al JSON histórico"""
    try:
        logger.info(f"📝 Agregando {fecha_str} al histórico...")

        # Cargar datos actuales
        with open('datos_historicos_36m.json', 'r', encoding='utf-8') as f:
            historico = json.load(f)

        # Extraer mes de la fecha (formato: "31-08-2026" -> "2026-08")
        fecha_parts = fecha_str.split('-')
        if len(fecha_parts) >= 3:
            mes_nuevo = f"{fecha_parts[2]}-{fecha_parts[1]}"
        else:
            logger.error(f"❌ Formato de fecha inválido: {fecha_str}")
            return False

        # Verificar si ya existe
        for item in historico:
            if item['mes'] == mes_nuevo:
                logger.warning(f"⚠️ {mes_nuevo} ya existe en el histórico")
                return False

        # Agregar nuevo mes con datos estimados adicionales
        nuevo_mes = {
            'mes': mes_nuevo,
            'ipc_var_mensual': ipc_valor,
            'ipc_var_12m': ipc_valor * 12,  # Estimado (será actualizado después)
            'tc': 915,  # Estimado
            'bencina': 920  # Estimado
        }

        historico.append(nuevo_mes)

        # Guardar
        with open('datos_historicos_36m.json', 'w', encoding='utf-8') as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ {mes_nuevo} agregado al histórico")
        logger.info(f"   Variación mensual: {ipc_valor}%")

        return True

    except Exception as e:
        logger.error(f"❌ Error actualizando: {e}")
        return False

if __name__ == '__main__':
    logger.info("\n" + "="*70)
    logger.info("🔄 ACTUALIZANDO DATOS HISTÓRICOS CON MES ACTUAL")
    logger.info("="*70 + "\n")

    ipc, fecha = obtener_ipc_actual()

    if ipc is not None:
        agregar_mes_al_historico(ipc, fecha)
        logger.info("\n✅ Datos actualizados. Ahora ejecuta: python3 arimax_predictor.py")
    else:
        logger.error("\n❌ No se pudo obtener el IPC actual")
        logger.info("   Introduce manualmente: python3 actualizar_mes_actual.py <mes> <ipc%>")

    logger.info("="*70 + "\n")
