# ⚙️ Setup GitHub Actions para Actualización Automática

## 📋 Lo que hemos creado

✅ Sistema de **cache inteligente** con TTL
✅ **GitHub Actions** para actualización automática
✅ Ejecución **cada lunes a las 09:00 UTC** (04:00 Chile)
✅ **Costo: $0**

---

## 🚀 Instalación (3 pasos)

### Paso 1: Hacer Push a GitHub
```bash
cd /Users/felipealdunate/Desktop/Desarrollo/IPC
bash push_a_github.sh
```

Esto:
- Agrega todos los archivos
- Hace commit con mensaje descriptivo
- Pushea a https://github.com/faldunero/ipc

### Paso 2: Agregar Secret en GitHub
1. Ir a: **https://github.com/faldunero/ipc/settings/secrets/actions**
2. Click en **"New repository secret"**
3. Nombre: `GROQ_API_KEY`
4. Valor: Tu API key de Groq
5. Click en **"Add secret"**

### Paso 3: Ejecutar Test (Opcional)
1. Ir a: **https://github.com/faldunero/ipc/actions**
2. Seleccionar workflow: "Actualizar Datos Macroeconómicos IPC"
3. Click en **"Run workflow"** → **"Run workflow"**
4. Ver ejecución en tiempo real ✅

---

## 📊 Qué Hace Automáticamente

**Cada lunes a las 09:00 UTC (04:00 Chile):**

```
GitHub Actions ejecuta:
  ↓
python3 actualizar_datos_macro.py
  ↓
1. Carga cache_datos_macro.json
2. Checkea TTL de cada dato
3. Actualiza datos viejos desde fuentes
4. Guarda cambios en el repo
  ↓
Tu cache siempre está actualizado ✅
```

---

## 🔍 Monitorear Ejecuciones

### Ver logs de ejecución
1. https://github.com/faldunero/ipc/actions
2. Click en el último run
3. Expandir "Actualizar datos macro" para ver logs detallados

### Si falla:
- Ver sección "Logs" para error específico
- Verificar que `GROQ_API_KEY` esté agregado en Secrets
- Ejecutar manualmente para debugging:
  ```bash
  python3 actualizar_datos_macro.py
  ```

---

## 📈 Estructura de Archivos Creados

```
.github/
└── workflows/
    └── actualizar-datos.yml    ← GitHub Actions workflow
    
cache_datos_macro.json         ← Cache inteligente
datos_macro_manager.py         ← Manager de datos
actualizar_datos_macro.py      ← Script de actualización
app_cron_endpoint.py          ← API endpoint (Railway)

requirements.txt               ← Dependencias
Dockerfile                     ← Para Railway
railway.json                   ← Config Railway

CACHE_SYSTEM.md               ← Documentación
AUTOMATIZACION.md
DEPLOY_RAILWAY_VERCEL.md
```

---

## ✅ Checklist

- [ ] Ejecutar `bash push_a_github.sh`
- [ ] Ir a GitHub Settings → Secrets
- [ ] Agregar `GROQ_API_KEY`
- [ ] Ir a Actions y ejecutar workflow manualmente
- [ ] Ver que todo se ejecuta correctamente ✅

---

## 🎯 Resultado Final

**Antes:**
❌ Datos hardcodeados
❌ Actualizaciones manuales
❌ Consultas redundantes

**Ahora:**
✅ Cache inteligente
✅ Actualización automática cada lunes
✅ Zero latencia (lee del cache local)
✅ Totalmente automatizado
✅ **Costo: $0**

---

## 🔗 Enlaces Importantes

- Repo: https://github.com/faldunero/ipc
- Actions: https://github.com/faldunero/ipc/actions
- Secrets: https://github.com/faldunero/ipc/settings/secrets/actions

