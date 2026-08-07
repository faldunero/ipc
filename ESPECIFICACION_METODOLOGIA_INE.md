# Especificación Técnica: Modelo Predictivo IPC conforme a Metodología INE

## 1. ENTENDIMIENTO CRÍTICO DE LA METODOLOGÍA

### 1.1 Ventana de Recolección
- **Período de levantamiento**: Día 1 a día 21 del mes M
- **Período de recuperación**: Días 22-23 (precios no disponibles)
- **Precios volátiles**: Hasta último día del mes (combustibles, pasajes interurbanos, transporte app)
- **Precios centralizados**: Corte al día 15 (electricidad, agua, telefonía, seguros, etc.)
- **Publicación**: Día 8 del mes M+1 (o próximo día hábil)

### 1.2 Lo que REALMENTE es el IPC publicado el 8 de septiembre
- **NO es**: "La inflación que pasó en agosto"
- **SÍ es**: Variación de precios medidos del 1-21 de agosto vs precios del mes anterior (julio)
- **Componentes**:
  - 70% precios de mercado regular (1-21)
  - 15% precios centralizados (corte día 15)
  - 15% precios volátiles (todo agosto)

## 2. PROBLEMA CON EL MODELO ACTUAL

### Versión INCORRECTA (actual)
```
Día 7 de Agosto → "Prediciendo IPC de Agosto"
Con datos de: Dólar, TPM, UF del día 7
Problema: Faltan 14 días más de recolección (1-21 = 21 días)
          Datos parciales ~33%, predicción débil
```

### Versión CORRECTA (esperada)
```
Durante Julio (1-21) → Recolectar precios
Día 8 de Agosto → Se publica IPC de Julio

Durante Agosto (1-21) → Recolectar precios NEW
Día 15 de Agosto → Corte de precios centralizados
Día 21 de Agosto → Fin de recolección regular
Día 8 de Septiembre → Se publica IPC de Agosto

Predicción óptima = Día 15+ de Agosto (tenemos 50%+ de datos reales)
Predicción fuerte = Día 21 de Agosto (tenemos 95%+ de datos reales)
```

## 3. DATOS QUE NECESITAMOS DURANTE LA VENTANA (1-21)

### Variables que IMPACTAN el IPC (pesos aproximados en canasta)
1. **Alimentación** (30%)
   - Precios ODEPA: frutas, verduras, lácteos
   - Precios minoristas: súper, mercados
   - Datos: Daily desde fuentes comerciales

2. **Transporte** (10%)
   - Precio combustible (bencinaenlinea.cl): actual
   - Valor UF: mensual (indexador)
   - Dólar: afecta vehículos importados

3. **Servicios Básicos** (15%)
   - Electricidad: Se publica mes anterior (día 15)
   - Agua potable: Se publica mes anterior
   - Gas: Se publica mes anterior
   - **Estos NO cambian día a día**, publicación puntual

4. **Vivienda** (15%)
   - Seguros de hogar
   - Mantenimiento
   - Publicación centralizada día 15

5. **Vestuario** (10%)
   - Índices Cámaras de Comercio
   - Recolección regular 1-21

6. **Diverso** (20%)
   - Educación
   - Salud
   - Comunicaciones

## 4. CRONOGRAMA CORRECTO DE PREDICCIÓN

### Semana 1 (Días 1-7 de M)
- **Estado**: Recolección inicial ~10-15% completada
- **Predicción**: DÉBIL, confianza baja
- **Modelo**: ARIMAX con datos incompletos
- **IC**: Ancho, ±1-1.5%

### Semana 2 (Días 8-14 de M)
- **Estado**: Recolección 30-40% completada
- **Predicción**: MEDIA, confianza moderada  
- **Modelo**: ARIMAX + pesos estimados en categorías incompletas
- **IC**: Moderado, ±0.7-1.0%

### Semana 3 (Días 15-21 de M)
- **Estado**: Recolección 95%+ completada
- **Predicción**: FUERTE, confianza alta
- **Modelo**: ARIMAX con 95% datos reales
- **IC**: Estrecho, ±0.3-0.5%

### Día 22+ (Después de publicación)
- **Estado**: Dato REAL publicado
- **Predicción**: Validar error vs real
- **Modelo**: Calcular MAE, RMSE, acierto direccional
- **Retroalimentación**: Ajustar pesos si necesario

## 5. VARIABLES EXÓGENAS POR CATEGORÍA

### Recolección DIARIA (1-21)
```json
{
  "fecha": "2026-08-15",
  "combustibles": {
    "bencina_93": 920.5,
    "diesel": 880.3,
    "fuente": "bencinaenlinea.cl",
    "actualizacion": "diaria"
  },
  "indices_comercio": {
    "ropa_calzado": 115.2,
    "electrodomesticos": 118.5,
    "muebles": 120.1,
    "tecnologia": 125.8,
    "alimentos_procesados": 112.3,
    "bebidas": 111.5,
    "fuente": "camaras_comercio.cl",
    "actualizacion": "semanal"
  },
  "agroindicadores": {
    "tomate_kg": 850,
    "lechuga_kg": 600,
    "papa_kg": 450,
    "zanahoria_kg": 550,
    "manzana_kg": 1200,
    "platano_kg": 800,
    "fuente": "odepa.cl",
    "actualizacion": "semanal"
  },
  "tasas_financieras": {
    "tpm": 4.50,
    "tasa_interbancaria": 4.45,
    "fuente": "mindicador.cl",
    "actualizacion": "diaria"
  },
  "tipo_cambio": {
    "dolar": 913.86,
    "uf": 40844.79,
    "utm": 71649.00,
    "fuente": "mindicador.cl",
    "actualizacion": "diaria"
  }
}
```

### Recolección CENTRALIZADA (Día 15)
```json
{
  "precios_centralizados_dia15": {
    "electricidad": "publica mes anterior, comparar vs mes actual",
    "agua_potable": "publica mes anterior, comparar vs mes actual",
    "gas_natural": "publica mes anterior, comparar vs mes actual",
    "telefonía": "publica mes anterior, comparar vs mes actual",
    "seguros_hogar": "publica mes anterior, comparar vs mes actual",
    "actualizacion": "puntual día 15"
  }
}
```

## 6. ESTRUCTURA DE PREDICCIÓN MEJORADA

### Input al modelo (Día N de la recolección)
```
IPC_histórico (36 meses reales)
↓
Variables exógenas del período 1 a N
↓
Estimación de variables ausentes (N+1 a 21)
↓
ARIMAX con pesos por completitud
↓
Predicción IPC_mes_M con IC
↓
Confianza = f(días_transcurridos, completitud_datos)
```

### Output
```json
{
  "mes_predicho": "2026-08",
  "dia_recoleccion": 15,
  "dias_completitud": "71% (15/21)",
  "prediccion_ipc": 0.42,
  "intervalo_confianza_95": {
    "min": 0.12,
    "max": 0.72
  },
  "confianza": "MEDIA",
  "variables_reales_usadas": 18,
  "variables_estimadas": 5,
  "modelo": "ARIMAX(1,1,1)",
  "fecha_prediccion": "2026-08-15T14:30:00",
  "fecha_validacion_esperada": "2026-09-08"
}
```

## 7. PIPELINE DE DATOS DIARIO

### Ejecución DIARIA a las 5:00 UTC (13:00 STP)
1. Ejecutar `recolectar_datos_diarios.py`
   - Fetch mindicador.cl (dólar, UF, TPM, tasa)
   - Fetch bencinaenlinea.cl (combustibles)
   - Fetch odepa.cl (frutas/verduras) si martes/jueves
   - Fetch camaras_comercio.cl si día lunes
   - Guardar en `datos_recoleccion_diarios/2026-08-15.json`

2. Ejecutar `arimax_predictor_dinamico.py`
   - Cargar datos históricos (36 meses)
   - Cargar datos recolectados hasta hoy (1-N)
   - Estimar datos faltantes (N+1-21) con promedio móvil
   - Entrenar ARIMAX
   - Generar predicción con IC dinámico
   - Guardar en `prediccion_actual.json`

3. Actualizar dashboard en tiempo real
   - Mostrar predicción actual
   - Mostrar % completitud
   - Mostrar nivel de confianza
   - Mostrar IC

## 8. VALIDACIÓN (Después de publicación)

### Día 8 del mes M+1
1. INE publica IPC_real de mes M
2. Ejecutar `validar_prediccion.py`
   - Comparar `prediccion_final` vs `ipc_real`
   - Calcular error = |predicción - real|
   - Actualizar `historico_validaciones.json`
   - Gráfico: error por día de predicción (1, 8, 15, 21)

### Métrica de éxito
- MAE ≤ 0.25% (si predicción hecha el día 21)
- MAE ≤ 0.40% (si predicción hecha el día 15)
- MAE ≤ 0.60% (si predicción hecha el día 8)
- Acierto direccional ≥ 75%

## 9. PRÓXIMAS ACCIONES

1. [ ] Rediseñar `arimax_predictor.py` con lógica de completitud
2. [ ] Crear `recolector_diario_completo.py` con todas las fuentes
3. [ ] Crear `estimador_variables_faltantes.py`
4. [ ] Crear dashboard con % completitud y confianza dinámica
5. [ ] Programar ejecución diaria a las 13:00 STP
6. [ ] Crear validador post-publicación INE
7. [ ] Documentar cambios en METODOLOGIA.md

---

**Versión**: 1.0  
**Fecha**: 2026-08-07  
**Estado**: ESPECIFICACIÓN LISTA PARA IMPLEMENTACIÓN
