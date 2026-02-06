#!/bin/bash
set -e

VPS_HOST="root@72.60.89.5"
VPS_DIR="/root/empatia_backend_modular"

echo "========================================="
echo "EmpatIA - Update to Neural2 Voice"
echo "========================================="
echo ""

# 1. Stop current container
echo "1. Parando container atual..."
ssh -t $VPS_HOST "docker stop empatia-backend-modular && docker rm empatia-backend-modular"
echo "✅ Container parado"
echo ""

# 2. Update .env with Neural2
echo "2. Atualizando .env para Neural2..."
scp .env.vps $VPS_HOST:$VPS_DIR/.env
echo "✅ .env atualizado (Neural2: pt-PT-Neural2-D)"
echo ""

# 3. Start new container (reusing existing image)
echo "3. Iniciando container com Neural2..."
ssh -t $VPS_HOST "cd $VPS_DIR && docker run -d \
    --name empatia-backend-modular \
    --restart unless-stopped \
    --network host \
    --env-file .env \
    -v $VPS_DIR/vertex-key.json:/app/vertex-key.json:ro \
    -v $VPS_DIR/logs:/app/logs \
    empatia-backend:modular"
echo "✅ Container iniciado"
echo ""

# 4. Wait and check
echo "4. Aguardando startup (5s)..."
sleep 5
echo ""

# 5. Check logs
echo "5. Verificando logs..."
ssh -t $VPS_HOST "docker logs --tail 20 empatia-backend-modular 2>&1 | grep -E '(Configuração|TTS|Neural2|PRONTO)' || docker logs --tail 5 empatia-backend-modular"
echo ""

# 6. Check status
echo "6. Status final:"
ssh -t $VPS_HOST "docker ps --filter 'name=empatia-backend-modular' --format 'table {{.Names}}\t{{.Status}}'"
echo ""

echo "========================================="
echo "✅ UPDATE COMPLETO!"
echo "========================================="
echo ""
echo "Voz Neural2: pt-PT-Neural2-D"
echo "Backend: ws://72.60.89.5:8765"
echo ""
