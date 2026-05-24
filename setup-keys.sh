#!/bin/bash
# Anti Setup - Configuración de API Keys (Privada y Local)
# ================================================
# Este script NUNCA sube tus keys a ningún lado.
# Solo configura variables locales en tu entorno.

set -e

echo "🔐 Anti - Configuración de API Keys"
echo "============================"
echo "Tus keys se configuran LOCALMENTE en tu entorno."
echo "NUNCA se suben a GitHub ni a ningún servidor."
echo

# Función para configurar key
set_key() {
    local provider=$1
    local env_var=$2
    local example=$3
    
    echo "📌 $provider"
    echo "   Ejemplo: $example"
    echo -n "   API Key (dejar vacío para skip): "
    read -s key
    echo
    
    if [ -n "$key" ]; then
        # Agregar a .bashrc o .zshrc (solo si no existe)
        local rc_file=~/.bashrc
        [ -f ~/.zshrc ] && rc_file=~/.zshrc
        
        # Check si ya existe
        if ! grep -q "export $env_var=" "$rc_file" 2>/dev/null; then
            echo "export $env_var='$key'" >> "$rc_file"
            echo "   ✅ Agregado a $rc_file"
        else
            echo "   ⚠️  Ya configurado en $rc_file"
        fi
        
        # Exportar para esta sesión
        export "$env_var=$key"
        echo "   ✅ Listo para esta sesión"
    else
        echo "   ⏭️  Skippeado"
    fi
    echo
}

# LM Studio (no requiere key)
echo "📌 LM Studio"
echo "   URL por defecto: http://127.0.0.1:1234/v1"
echo "   No requiere API key."
echo

# Ollama (no requiere key)
echo "📌 Ollama"
echo "   URL por defecto: http://127.0.0.1:11434"
echo "   No requiere API key."
echo

# OpenAI
set_key "OpenAI" "OPENAI_API_KEY" "sk-..."

# Gemini  
set_key "Google Gemini" "GEMINI_API_KEY" "AI..."

echo "================================"
echo "✅ Configuración completa!"
echo
echo "Para activar en esta sesión:"
echo "  source ~/.bashrc"
echo ""
echo "Para verificar:"
echo "  echo \$OPENAI_API_KEY"
echo "  echo \$GEMINI_API_KEY"