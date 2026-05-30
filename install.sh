#!/bin/bash

# Colores para el script
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando instalación de Anti...${NC}"

# 1. Crear entorno virtual
echo -e "\n${BLUE}📦 Creando entorno virtual...${NC}"
python3 -m venv venv
source venv/bin/activate

# 2. Instalar dependencias
echo -e "\n${BLUE}📥 Instalando dependencias...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
# Install rich for the launcher to look even better (optional but recommended)
pip install rich

# 3. Compilar Ejecutable Go
echo -e "\n${BLUE}🏗️ Compilando lanzador estático en Go...${NC}"
if command -v go &> /dev/null; then
    cd cmd/tui
    go build -o ../../anti .
    cd ../..
    echo -e "${GREEN}✅ Lanzador Go compiled successfully.${NC}"
else
    echo -e "${RED}⚠️ Go no está instalado. Se ejecutará el agente directamente desde main.py.${NC}"
fi

# 4. Configurar Alias
echo -e "\n${BLUE}🔗 Configurando alias 'anti' en .bashrc...${NC}"
if [ -f "./anti" ]; then
    ALIAS_LINE="alias anti='$(pwd)/anti'"
else
    ALIAS_LINE="alias anti='$(pwd)/venv/bin/python $(pwd)/main.py'"
fi

if grep -q "alias anti=" ~/.bashrc; then
    # Actualizar alias existente
    sed -i "s|alias anti=.*|$ALIAS_LINE|" ~/.bashrc
    echo -e "${GREEN}✅ Alias 'anti' actualizado.${NC}"
else
    # Agregar nuevo alias
    echo "$ALIAS_LINE" >> ~/.bashrc
    echo -e "${GREEN}✅ Alias 'anti' agregado.${NC}"
fi

echo -e "\n${GREEN}✨ ¡Instalación completada con éxito!${NC}"
echo -e "Para empezar a usarlo, ejecutá: source ~/.bashrc y luego simplemente escribe anti"
