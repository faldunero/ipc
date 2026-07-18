#!/bin/bash
#
# Setup de automatización para IPC Predictor
# Configura cron jobs y directorios necesarios
# Uso: bash setup_cron.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN=$(which python3)
PIP_BIN=$(which pip3 || which pip)

# Si no hay pip, intentar python3 -m pip
if [ -z "$PIP_BIN" ]; then
    PIP_BIN="$PYTHON_BIN -m pip"
fi

echo "=========================================="
echo "📊 IPC PREDICTOR - Setup Automatización"
echo "=========================================="
echo ""

# 1. Crear directorio de logs
echo "📁 Creando directorio de logs..."
mkdir -p "${SCRIPT_DIR}/logs"
chmod 755 "${SCRIPT_DIR}/logs"
echo "✅ Directorio creado: ${SCRIPT_DIR}/logs"
echo ""

# 2. Hacer script ejecutable
echo "🔧 Haciendo scripts ejecutables..."
chmod +x "${SCRIPT_DIR}/actualizar_datos_macro.py"
chmod +x "${SCRIPT_DIR}/datos_macro_manager.py"
echo "✅ Scripts con permisos de ejecución"
echo ""

# 3. Verificar dependencias Python
echo "📦 Verificando dependencias Python..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo "⚠️  Instalando requests..."
    $PIP_BIN install requests || echo "❌ Error instalando requests"
fi
if ! python3 -c "import bs4" 2>/dev/null; then
    echo "⚠️  Instalando beautifulsoup4..."
    $PIP_BIN install beautifulsoup4 || echo "❌ Error instalando beautifulsoup4"
fi
echo "✅ Dependencias OK"
echo ""

# 4. Configurar cron
echo "⏰ Configurando cron job..."
echo ""
echo "Selecciona frecuencia de actualización:"
echo "1) Diariamente a las 09:00"
echo "2) 2x/mes (días 1 y 15) a las 09:00"
echo "3) Semanalmente (lunes a las 09:00)"
echo ""
read -p "Opción [1-3]: " option

case $option in
    1)
        CRON_SCHEDULE="0 9 * * *"
        FREQ="DIARIAMENTE a las 09:00"
        ;;
    2)
        CRON_SCHEDULE="0 9 1,15 * *"
        FREQ="2x/mes (días 1 y 15) a las 09:00"
        ;;
    3)
        CRON_SCHEDULE="0 9 * * 1"
        FREQ="SEMANALMENTE (lunes) a las 09:00"
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

# Crear entrada de cron
CRON_JOB="${CRON_SCHEDULE} cd ${SCRIPT_DIR} && ${PYTHON_BIN} actualizar_datos_macro.py >> ${SCRIPT_DIR}/logs/actualizacion.log 2>&1"

# Guardar cron actual
TEMP_CRON=$(mktemp)
crontab -l > "$TEMP_CRON" 2>/dev/null || true

# Verificar si ya existe
if grep -q "actualizar_datos_macro.py" "$TEMP_CRON"; then
    echo "⚠️  Cron job ya existe. Reemplazando..."
    grep -v "actualizar_datos_macro.py" "$TEMP_CRON" > "${TEMP_CRON}.new"
    mv "${TEMP_CRON}.new" "$TEMP_CRON"
fi

# Agregar nueva entrada
echo "$CRON_JOB" >> "$TEMP_CRON"

# Instalar cron actualizado
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

echo "✅ Cron configurado: $FREQ"
echo "   Comando: $CRON_JOB"
echo ""

# 5. Verificar instalación
echo "✔️  Verificando instalación..."
echo ""
echo "Cron jobs activos:"
crontab -l | grep "actualizar_datos_macro.py" || echo "⚠️  No se encontró el job"
echo ""

# 6. Test de funcionamiento
echo "🧪 Ejecutando test..."
cd "$SCRIPT_DIR"
if python3 actualizar_datos_macro.py; then
    echo "✅ Test exitoso"
else
    echo "❌ Error en test"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ SETUP COMPLETADO"
echo "=========================================="
echo ""
echo "Próxima actualización: $FREQ"
echo "Logs: ${SCRIPT_DIR}/logs/actualizacion.log"
echo ""
echo "Para desactivar, ejecutar:"
echo "  crontab -e"
echo "  # Comentar o eliminar línea con 'actualizar_datos_macro.py'"
echo ""
echo "Para ver logs en tiempo real:"
echo "  tail -f ${SCRIPT_DIR}/logs/actualizacion.log"
echo ""
