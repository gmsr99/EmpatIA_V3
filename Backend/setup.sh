#!/bin/bash
# Script de setup para o EmpatIA Backend

set -e

echo "==================================="
echo "EmpatIA Backend - Setup"
echo "==================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION encontrado"

# Criar ambiente virtual
if [ ! -d "venv" ]; then
    echo "📦 A criar ambiente virtual..."
    python3 -m venv venv
    echo "✅ Ambiente virtual criado"
else
    echo "✅ Ambiente virtual já existe"
fi

# Ativar ambiente virtual
source venv/bin/activate

# Upgrade pip
echo "📦 A atualizar pip..."
pip install --upgrade pip > /dev/null 2>&1

# Instalar dependências
echo "📦 A instalar dependências..."
pip install -r requirements.txt

echo ""
echo "✅ Instalação concluída!"
echo ""
echo "Próximos passos:"
echo "1. Copie .env.example para .env"
echo "   $ cp .env.example .env"
echo ""
echo "2. Edite .env com as suas credenciais"
echo "   $ nano .env"
echo ""
echo "3. Execute o servidor"
echo "   $ python main.py"
echo ""
