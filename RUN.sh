#!/bin/bash

echo "🚀 Iniciando Predictor IPC con Frontend"
echo ""

# Verificar .env
if [ ! -f .env ]; then
    echo "❌ Falta archivo .env"
    echo "Ejecuta primero: bash setup.sh"
    exit 1
fi

# Cargar variables de entorno
export $(cat .env | grep -v '^#' | xargs)

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install -r requirements.txt --break-system-packages -q

echo ""
echo "✅ Dependencias instaladas"
echo ""
echo "🌐 Iniciando servidor en http://localhost:8000"
echo ""
echo "Presiona Ctrl+C para detener"
echo ""

# Ejecutar FastAPI
python app.py
