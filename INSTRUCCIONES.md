# INSTRUCCIONES DE FORMATO - IPC PREDICTOR

## Formato de Números - Convención Chilena

**REGLA CRÍTICA:** Todos los porcentajes y decimales deben mostrase en **formato chileno** usando coma como separador decimal.

### Ejemplos correctos:
- ✅ `39,60%` (no 39.60%)
- ✅ `4,2%` (no 4.2%)
- ✅ `5,5%` (no 5.5%)
- ✅ `+0,6%` (no +0.6%)

### Función de Formato
```javascript
function formatearChile(num, decimales = 2) {
    return parseFloat(num).toFixed(decimales).replace('.', ',');
}
```

### Lugares donde se aplica:
1. **Métricas en Dashboard** - IPC Actual, IPC Futuro, Variación
2. **Tabla Histórica** - Todos los porcentajes
3. **Excel Export** - Resumen y proyecciones
4. **Gráficos** - Etiquetas de valores

---

## Estructura del Proyecto

```
/IPC/
  ├── index.html          → Dashboard (Frontend)
  ├── app.py              → API FastAPI
  ├── ipc_predictor.py    → Modelo de predicción
  ├── .env                → Configuración (nunca compartir)
  └── INSTRUCCIONES.md    → Este archivo
```

---

## Claves de API (No Compartir)

- **GROQ_API_KEY**: Para predicciones con IA
- **SUPABASE_URL**: Base de datos
- **SUPABASE_KEY**: Autenticación

---

## Inicio Rápido

```bash
python3 app.py
# http://localhost:8000
```
