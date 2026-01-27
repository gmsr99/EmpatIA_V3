#!/bin/bash
# Script para descobrir configuração do PostgreSQL existente

echo "🔍 Procurando container PostgreSQL..."
echo ""

# Encontrar containers com 'postgres' no nome
POSTGRES_CONTAINERS=$(docker ps --format "{{.Names}}" | grep -i postgres)

if [ -z "$POSTGRES_CONTAINERS" ]; then
    echo "❌ Nenhum container PostgreSQL encontrado rodando!"
    echo ""
    echo "Containers ativos:"
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
    exit 1
fi

echo "📦 Containers PostgreSQL encontrados:"
echo "$POSTGRES_CONTAINERS"
echo ""

# Para cada container encontrado
for container in $POSTGRES_CONTAINERS; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Container: $container"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Rede
    NETWORK=$(docker inspect $container --format '{{range $key, $value := .NetworkSettings.Networks}}{{$key}}{{end}}')
    echo "🌐 Rede: $NETWORK"

    # IP
    IP=$(docker inspect $container --format '{{range $key, $value := .NetworkSettings.Networks}}{{$value.IPAddress}}{{end}}')
    echo "📍 IP: $IP"

    # Portas
    PORTS=$(docker inspect $container --format '{{range $p, $conf := .NetworkSettings.Ports}}{{$p}} -> {{(index $conf 0).HostPort}}{{end}}')
    echo "🔌 Portas: $PORTS"

    # Hostname interno
    HOSTNAME=$(docker inspect $container --format '{{.Config.Hostname}}')
    echo "🏷️  Hostname: $HOSTNAME"

    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 CONFIGURAÇÃO RECOMENDADA"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "No arquivo docker-compose.yml, use:"
echo ""
echo "networks:"
echo "  empatia_network:"
echo "    external: true"
echo "    name: $NETWORK"
echo ""
echo "No arquivo .env, use:"
echo "POSTGRES_HOST=$container  # Nome do container"
echo "# ou"
echo "POSTGRES_HOST=$IP  # IP direto"
echo ""
