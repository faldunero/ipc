#!/bin/bash

# Setup para Predictor de IPC con Groq + Supabase

echo "🚀 Configurando predictor IPC..."

# Instalar dependencias
pip install groq pandas requests numpy --break-system-packages

# Solicitar claves
echo ""
echo "📝 Ingresa tus credenciales:"
echo ""

read -p "API Key de Groq (https://console.groq.com): " GROQ_KEY
read -p "URL de Supabase (ej: https://xxxxx.supabase.co): " SUPABASE_URL
read -p "API Key de Supabase (anon key): " SUPABASE_KEY

# Guardar en .env
cat > .env << EOF
GROQ_API_KEY=$GROQ_KEY
SUPABASE_URL=$SUPABASE_URL
SUPABASE_KEY=$SUPABASE_KEY
EOF

echo ""
echo "✅ Configuración guardada en .env"
echo ""
echo "Para ejecutar el predictor:"
echo "  python ipc_predictor.py"
