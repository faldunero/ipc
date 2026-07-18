#!/bin/bash
#
# Script para push automático de cambios a GitHub
# Uso: bash push_a_github.sh
#

set -e

echo "=========================================="
echo "📤 PUSH A GITHUB - IPC PREDICTOR"
echo "=========================================="
echo ""

REPO_URL="https://github.com/faldunero/ipc"

# 1. Verificar que estamos en el repo correcto
if [ ! -d ".git" ]; then
    echo "⚠️  No estamos en un repo Git"
    echo "Inicializando..."
    git init
    git remote add origin $REPO_URL
fi

# 2. Verificar cambios
echo "📊 Estado del repo:"
git status --short || true
echo ""

# 3. Agregar archivos
echo "📝 Agregando archivos..."
git add .

# 4. Commit
echo "💬 Haciendo commit..."
git commit -m "🚀 Agregar sistema de cache + GitHub Actions para actualización automática

- cache_datos_macro.json: Buffer inteligente con 13+ métricas
- datos_macro_manager.py: Manager con TTL y auto-actualización
- actualizar_datos_macro.py: Script ejecutable
- .github/workflows/actualizar-datos.yml: GitHub Actions (lunes 09:00 UTC)
- requirements.txt: Dependencias Python
- Dockerfile: Para Railway/Vercel
- Documentación completa: CACHE_SYSTEM.md, AUTOMATIZACION.md, DEPLOY_RAILWAY_VERCEL.md"

# 5. Push
echo "🚀 Haciendo push a GitHub..."
git push -u origin main || git push -u origin master || echo "⚠️  Intenta push manual"

echo ""
echo "=========================================="
echo "✅ PUSH COMPLETADO"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Ir a: https://github.com/faldunero/ipc/settings/secrets/actions"
echo "2. Crear Secret: GROQ_API_KEY = tu_groq_api_key"
echo "3. GitHub Actions se ejecutará cada lunes a las 09:00 UTC"
echo "4. Ver ejecuciones en: https://github.com/faldunero/ipc/actions"
echo ""
