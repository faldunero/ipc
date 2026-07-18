# Sistema de Actualización Automática - Datos Macroeconómicos IPC Predictor

## 📋 Descripción

El sistema IPC Predictor ahora tiene:
- **Cache inteligente** (`cache_datos_macro.json`) que evita consultas innecesarias
- **TTL por dato** (Time To Live) - cada dato tiene política de actualización diferente
- **Actualización automática** vía scheduled task
- **Logging centralizado** en `logs/actualizacion.log`

## 🔄 Política de Actualización (TTL)

| Dato | Frecuencia | Fuente | TTL |
|------|-----------|--------|-----|
| Tipo de cambio CLP/USD | Diaria | Banco Central Chile | 24h |
| Petróleo Brent | Diaria | Trading Economics | 24h |
| Cobre Comex | Diaria | CME Group | 24h |
| Tasas Fed | Diaria | Federal Reserve | 24h |
| Inflación EEUU | Mensual | BLS | 30d |
| Presión salarial | Semanal | BC encuestas | 7d |
| Desempleo Chile | Trimestral | INE | 90d |
| Meta inflación BC | Mensual | Banco Central | 30d |
| Alimentos FAO | Mensual | FAO | 30d |

## 🛠️ Instalación

### 1. Dependencias Python
```bash
pip install requests beautifulsoup4
```

### 2. Crear directorio de logs
```bash
mkdir -p logs
```

## ⚙️ Configurar Actualización Automática

### Opción A: LINUX / MAC (usando crontab)

#### Configuración simple (diaria a las 9:00 AM)
```bash
crontab -e
```

Agregar línea:
```cron
0 9 * * * cd /Users/felipealdunate/Desktop/Desarrollo/IPC && python3 actualizar_datos_macro.py >> logs/actualizacion.log 2>&1
```

#### Configuración recomendada (2x/mes: días 1 y 15)
```cron
# Actualizar el 1 y 15 de cada mes a las 09:00
0 9 1,15 * * cd /Users/felipealdunate/Desktop/Desarrollo/IPC && python3 actualizar_datos_macro.py >> logs/actualizacion.log 2>&1
```

#### Validar cron fue guardado
```bash
crontab -l
```

---

### Opción B: WINDOWS (usando Task Scheduler)

#### Paso 1: Abrir Task Scheduler
```
Windows + R → "taskschd.msc"
```

#### Paso 2: Crear Tarea Nueva
1. Panel derecho: **Crear tarea básica**
2. Nombre: `IPC_Actualizar_Datos_Macro`
3. Descripción: `Actualiza datos macroeconómicos para predicción IPC`
4. Siguiente >

#### Paso 3: Configurar Disparador
1. Seleccionar: **Diariamente**
2. Hora: **09:00**
3. Repetir cada: **15 días** (para 2x/mes)
4. Siguiente >

#### Paso 4: Configurar Acción
1. **Iniciar un programa**
2. Programa: `C:\Users\felipealdunate\AppData\Local\Programs\Python\Python311\python.exe`
3. Argumentos: `C:\Users\felipealdunate\Desktop\Desarrollo\IPC\actualizar_datos_macro.py`
4. Iniciar en: `C:\Users\felipealdunate\Desktop\Desarrollo\IPC`
5. Siguiente >

#### Paso 5: Finalizar
- ✅ Abrir la carpeta de propiedades
- Finish

#### Opcional: Ejecutar manualmente
```
botón derecho en tarea → Ejecutar
```

---

### Opción C: SYSTEMD (Linux moderno)

Crear archivo `/etc/systemd/system/ipc-actualizar.service`:
```ini
[Unit]
Description=IPC Predictor - Actualizar Datos Macro
After=network.target

[Service]
Type=oneshot
User=tu_usuario
WorkingDirectory=/Users/felipealdunate/Desktop/Desarrollo/IPC
ExecStart=/usr/bin/python3 actualizar_datos_macro.py
StandardOutput=append:/Users/felipealdunate/Desktop/Desarrollo/IPC/logs/actualizacion.log
StandardError=append:/Users/felipealdunate/Desktop/Desarrollo/IPC/logs/actualizacion.log

[Install]
WantedBy=multi-user.target
```

Crear timer (`/etc/systemd/system/ipc-actualizar.timer`):
```ini
[Unit]
Description=IPC Predictor - Timer de Actualización
Requires=ipc-actualizar.service

[Timer]
# Ejecutar a las 9:00 AM cada día
OnCalendar=*-*-* 09:00:00
# Alternativa: 2x/mes
OnCalendar=*-*-{01,15} 09:00:00

[Install]
WantedBy=timers.target
```

Activar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ipc-actualizar.timer
sudo systemctl start ipc-actualizar.timer
sudo systemctl status ipc-actualizar.timer
```

---

## 📊 Uso en el Código (ipc_predictor.py)

### Antes (hardcodeado):
```python
factores_internos = [
    "Mercado laboral: Desempleo 9,4%...",
    "Tipo de cambio: 934,96 CLP/USD...",
]
```

### Ahora (desde cache):
```python
from datos_macro_manager import DatosMacroManager

manager = DatosMacroManager()

# Obtiene del cache, auto-actualiza si está viejο
factores_internos = manager.obtener_todos_factores_internos()
factores_externos = manager.obtener_todos_factores_externos()

# Usar en predicción...
resultado = {
    "factores_internos": factores_internos,
    "factores_externos": factores_externos,
}
```

---

## 📝 Monitoreo

### Ver logs en tiempo real (Linux/Mac)
```bash
tail -f logs/actualizacion.log
```

### Ver logs en Windows
```cmd
type logs\actualizacion.log
```

### Estructura de log
```
2026-07-18 09:00:01 - datos_macro_manager - INFO - ✅ Cache de datos macro cargado
2026-07-18 09:00:02 - datos_macro_manager - INFO - 🔄 Iniciando actualización...
2026-07-18 09:00:03 - datos_macro_manager - INFO - ✅ tipo_cambio actualizado
2026-07-18 09:00:04 - datos_macro_manager - INFO - ✅ petroleo_brent actualizado
...
```

---

## 🔍 Validar Funcionamiento

### Test manual
```python
from datos_macro_manager import DatosMacroManager

manager = DatosMacroManager()

# Verificar cache cargado
print("Cache timestamp:", manager.cache.get('ultima_actualizacion'))

# Obtener un dato
desempleo = manager.obtener_dato('desempleo', auto_actualizar=False)
print(f"Desempleo: {desempleo['valor']}%")

# Forzar actualización
manager.actualizar_todos()
```

### Test de cron (Linux)
```bash
# Ver si se ejecutó
grep "ACTUALIZACIÓN" logs/actualizacion.log | tail -5

# Verificar si cache fue actualizado
stat -c '%y' cache_datos_macro.json
```

---

## ⚠️ Troubleshooting

### "No module named 'BeautifulSoup'"
```bash
pip install beautifulsoup4
```

### "Permission denied" en cron
```bash
chmod +x actualizar_datos_macro.py
```

### Cron no se ejecuta
1. Verificar que Python está en PATH:
   ```bash
   which python3
   ```
2. Usar path absoluto en crontab

### Logs no se crean
```bash
mkdir -p logs
chmod 755 logs
```

---

## 🚀 Próximas Mejoras

- [ ] Integración con APIs reales (Banco Central, INE, COMEX)
- [ ] Notificaciones por email si falla actualización
- [ ] Dashboard de health check
- [ ] Rollback automático si datos inconsistentes
- [ ] Sincronización con PostgreSQL para backup

---

## 📞 Contacto

Para preguntas sobre la configuración, revisar logs o contactar.
