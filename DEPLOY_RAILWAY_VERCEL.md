# Deploy en Railway / Vercel + Cron Automático

## 🚀 El Problema

**Cron tradicional NO funciona en:**
- Vercel (serverless, sin procesos background)
- Railway (si no configuras workers)
- AWS Lambda, Google Cloud Functions, etc

**Solución:** Usar **endpoint HTTP + servicio de cron externo** (EasyCron, GitHub Actions)

---

## 📋 Opción 1: Railway + EasyCron (RECOMENDADO)

### Paso 1: Deploy en Railway
```bash
cd /Users/felipealdunate/Desktop/Desarrollo/IPC

# Crear archivo railway.json
cat > railway.json << 'EOF'
{
  "build": {
    "builder": "dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "startCommand": "python3 app.py"
  }
}
EOF

# Crear Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
EXPOSE $PORT

CMD ["python3", "app.py"]
EOF

# Crear requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn==0.24.0
requests==2.31.0
beautifulsoup4==4.12.2
pandas==2.1.0
statsmodels==0.14.0
groq==0.4.1
python-dotenv==1.0.0
EOF

# Push a Railway
railway up
```

### Paso 2: Anotar URL de Railway
```
Ejemplo: https://ipc-predictor-production.railway.app
```

### Paso 3: Configurar Token en Railway
```bash
railway variable add CRON_TOKEN=tu_token_muy_secreto_aqui_12345
railway variable add GROQ_API_KEY=tu_groq_key
```

### Paso 4: Configurar EasyCron (Gratis)
1. Ir a: https://www.easycron.com
2. Sign up (gratis)
3. Crear nuevo cron job:
   - **URL:** `https://ipc-predictor-production.railway.app/api/actualizar-datos-macro?token=tu_token_muy_secreto_aqui_12345`
   - **Frecuencia:** Weekly (Mondays 09:00)
   - **Notification:** Email si falla
4. Guardar

**✅ LISTO** - Cada lunes a las 09:00 UTC, EasyCron llamará tu endpoint

---

## 📋 Opción 2: Vercel + GitHub Actions (Alternativa)

### Paso 1: Deploy FastAPI en Railway (Vercel NO soporta FastAPI)
Railway será el backend, Vercel solo el frontend:

```bash
# API en Railway (como Opción 1)

# Frontend en Vercel
# (Tu dashboard con ipc_predictor.py)
```

### Paso 2: GitHub Actions (Cron gratis)
Crear `.github/workflows/actualizar-datos.yml`:

```yaml
name: Actualizar Datos Macro

on:
  schedule:
    # Lunes a las 09:00 UTC
    - cron: '0 9 * * 1'

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install requests beautifulsoup4
      
      - name: Actualizar datos
        run: |
          curl -X GET "https://ipc-predictor-production.railway.app/api/actualizar-datos-macro?token=${{ secrets.CRON_TOKEN }}"
```

**✅ Gratis, ejecutado por GitHub**

---

## 📋 Opción 3: cron-job.org (Alternativa Simple)

1. Ir a: https://cron-job.org
2. Create cronjob:
   - **URL:** `https://ipc-predictor-production.railway.app/api/actualizar-datos-macro?token=tu_token`
   - **Execution time:** Weekly, Monday 09:00
   - **Notification:** Email
3. Save

**✅ Listo** - Servicio alemán muy confiable

---

## 🔐 Seguridad en Producción

### ❌ NO HACER:
```
?token=tu_token_super_secreto_aqui
```
Tokens en URLs son visibles en logs.

### ✅ HACER:
```bash
# En Railway Dashboard:
railway variable add CRON_TOKEN=tu_token_generado_aleatoriamente

# En app_cron_endpoint.py:
CRON_TOKEN = os.getenv("CRON_TOKEN")
```

### Generar token seguro:
```python
import secrets
print(secrets.token_urlsafe(32))
# Ejemplo: WkMGy5vQ_XzF9Lp7NkJhT2mB-uQr8sZ0
```

---

## 📊 Arquitectura Final (Railway)

```
┌─────────────────────────────────────────────┐
│          Servicios Externos (2x/sem)        │
│  EasyCron / GitHub Actions / cron-job.org   │
└──────────────────┬──────────────────────────┘
                   │ HTTP GET
                   │ /api/actualizar-datos-macro?token=***
                   ▼
┌─────────────────────────────────────────────┐
│         Railway (FastAPI Endpoint)          │
│   app_cron_endpoint.py + datos_macro_*      │
│   - Valida token                            │
│   - Actualiza cache_datos_macro.json        │
│   - Retorna JSON status                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
         cache_datos_macro.json
      (persiste en volumen Railway)
                   │
                   ▼
    app.py (predicción IPC)
   - Lee cache local
   - Genera predicciones
```

---

## 🧪 Testear en Local

```bash
# Terminal 1: Ejecutar servidor
cd /Users/felipealdunate/Desktop/Desarrollo/IPC
source venv/bin/activate
python3 app_cron_endpoint.py

# Terminal 2: Testear endpoint
curl "http://localhost:8000/api/actualizar-datos-macro?token=tu_token_super_secreto_aqui_12345"

# Respuesta esperada:
# {
#   "status": "success",
#   "message": "Datos actualizados correctamente",
#   "timestamp": "2026-07-18T10:30:00.123456",
#   "ultima_actualizacion": "2026-07-18T10:30:00"
# }
```

---

## ✅ Checklist Deployment

- [ ] Crear `Dockerfile` con Python 3.11+
- [ ] Crear `requirements.txt` con dependencias
- [ ] Push a Railway
- [ ] Obtener URL pública de Railway
- [ ] Generar `CRON_TOKEN` seguro
- [ ] Configurar variables en Railway
- [ ] Registrarse en EasyCron / GitHub Actions
- [ ] Probar endpoint manualmente:
  ```bash
  curl "https://tu-app.railway.app/api/actualizar-datos-macro?token=***"
  ```
- [ ] Ver logs en Railway dashboard
- [ ] Guardar URL en notas

---

## 🔍 Monitoreo en Producción

### Ver logs en Railway
```bash
railway logs
```

### Ver status del cache
```bash
# Sin autenticación (debugging)
curl "https://tu-app.railway.app/api/cache-status"

# Respuesta:
# {
#   "ultima_actualizacion": "2026-07-18T10:30:00",
#   "proxima_actualizacion": "2026-07-25T10:30:00",
#   "version": "1.0",
#   "datos_disponibles": 18
# }
```

---

## 💰 Costos

| Servicio | Costo |
|----------|-------|
| Railway | $5/mes (o gratis si <512MB) |
| EasyCron | Gratis |
| GitHub Actions | Gratis (2000 min/mes) |
| cron-job.org | Gratis |
| **Total** | **Gratis - $5/mes** |

---

## ⚠️ Troubleshooting

### "401 Unauthorized"
- ✅ Verificar token en Railway variables
- ✅ Verificar token en URL de cron

### "Cache no se actualiza"
- ✅ Ver logs en Railway: `railway logs`
- ✅ Testear manualmente: `curl /api/actualizar-datos-macro?token=...`

### "ModuleNotFoundError"
- ✅ Verificar `requirements.txt` en Dockerfile
- ✅ Reconstruir: `railway build`

---

## 🚀 Siguientes Pasos

1. Crear cuenta Railway si no tienes
2. Crear variables de entorno
3. Push a Railway
4. Registrarse en EasyCron
5. Configurar URL + token
6. Testear

¿Necesitas ayuda con algún paso?
