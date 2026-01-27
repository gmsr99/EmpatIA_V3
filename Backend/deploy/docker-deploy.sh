#!/bin/bash
# Script de deploy do backend EmpatIA usando Docker

set -e

echo "🐳 EmpatIA Backend - Deploy com Docker"
echo "======================================"

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado!"
    echo "Instale: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado!"
    echo "Instale: sudo apt install docker-compose"
    exit 1
fi

# Diretório de trabalho
DEPLOY_DIR="/opt/empatia"

echo "📁 Criando diretório de deploy..."
sudo mkdir -p $DEPLOY_DIR
sudo chown $USER:$USER $DEPLOY_DIR

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "❌ Arquivo .env não encontrado!"
    echo "Copie .env.example e configure:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Verificar se vertex-key.json existe
if [ ! -f vertex-key.json ]; then
    echo "❌ Arquivo vertex-key.json não encontrado!"
    echo "Copie o arquivo de credenciais do Google Cloud"
    exit 1
fi

echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Iniciando containers..."
docker-compose up -d

echo "⏳ Aguardando backend inicializar (30s)..."
sleep 30

# Verificar se está rodando
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Backend EmpatIA está rodando!"
    echo ""
    echo "📊 Status:"
    docker-compose ps
    echo ""
    echo "📝 Ver logs:"
    echo "  docker-compose logs -f empatia-backend"
    echo ""
    echo "🔄 Reiniciar:"
    echo "  docker-compose restart"
    echo ""
    echo "🛑 Parar:"
    echo "  docker-compose down"
else
    echo ""
    echo "❌ Erro ao iniciar backend!"
    echo "Ver logs: docker-compose logs empatia-backend"
    exit 1
fi
