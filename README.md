# Predictor de IPC Chile - Groq + Supabase

Modelo predictivo para forecasting del Índice de Precios al Consumidor usando IA de Groq.

## Arquitectura

```
INE (datos históricos)
    ↓
Python Script (fetch + análisis)
    ↓
Groq (predicción + análisis)
    ↓
Supabase (almacenamiento)
```

## Requisitos

- Python 3.9+
- Cuenta en [Groq](https://console.groq.com)
- Proyecto en [Supabase](https://supabase.com)

## Instalación

### 1. Clonar/Descargar archivos
```bash
ls ipc_predictor.py supabase_migrations.sql
```

### 2. Instalar dependencias
```bash
pip install groq pandas requests numpy --break-system-packages
```

### 3. Configurar Supabase

**En el dashboard de Supabase:**
- Abre SQL Editor
- Copia el contenido de `supabase_migrations.sql`
- Ejecuta para crear tablas

### 4. Configurar variables de entorno

Opción A - Con .env:
```bash
bash setup.sh
```

Opción B - Manual:
```bash
export GROQ_API_KEY="gsk_xxxxx"
export SUPABASE_URL="https://xxxxx.supabase.co"
export SUPABASE_KEY="eyJxxx"
```

## Uso

```bash
python ipc_predictor.py
```

Salida esperada:
```
🚀 Iniciando Predictor de IPC

📊 Descargando datos del INE...
✅ Datos cargados: 42 registros

🤖 Analizando con Groq...
📈 Análisis: ...

📌 PREDICCIÓN DEL PRÓXIMO MES:
  IPC Predicho: 140.25
  Variación esperada: +0.50
```

## Modelos Usados

1. **ARIMA Simple**: Extrapolación basada en últimos 6 meses
2. **Groq LLM**: Análisis contextual + predicción
3. **Hybrid**: Promedio ponderado (50/50)

## Estructura de Datos

### ipc_predicciones
- `mes_predicho`: Mes objetivo (YYYY-MM)
- `ipc_predicho`: Valor predicho
- `variacion_esperada`: Cambio respecto mes anterior
- `metodo`: Algoritmo usado

### ipc_historico
- Datos históricos del INE
- Categorías: alimentos, vivienda, transporte, etc.

### ipc_analisis
- Análisis de Groq
- Tendencias identificadas
- Factores de riesgo

## Mejoras Futuras

- Integrar datos reales del INE (web scraping/API)
- Modelos LSTM para series de tiempo
- Análisis multivariado con variables exógenas
- Dashboard en Streamlit/Dash

## Créditos

- Metodología: INE (Instituto Nacional de Estadísticas)
- IA: Groq (Mixtral-8x7b)
- Base de datos: Supabase
