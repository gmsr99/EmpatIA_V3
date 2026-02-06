#!/bin/bash
set -e

VPS_HOST="root@72.60.89.5"
VPS_BACKEND_DIR="/root/empatia_backend"
LOCAL_BACKEND_DIR="/Users/gmsr44/Desktop/EmpatIA/8. Website/1. Agente com ADK/3. EmpatIA V3/Backend"

echo "========================================="
echo "EmpatIA Backend - Deploy to VPS"
echo "Pipeline: Groq STT → Gemini Flash Lite → WaveNet TTS"
echo "========================================="
echo ""
echo "⚠️  You will be prompted for SSH password: 3f-O78sAL@e/?cDw,Q.D"
echo ""
read -p "Press Enter to continue..."
echo ""

# 1. Check running containers
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Checking running containers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t $VPS_HOST "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"
echo ""

# 2. Stop old backend
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Stopping old backend container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t $VPS_HOST "docker ps --filter 'name=empatia' -q | xargs -r docker stop && docker ps -a --filter 'name=empatia' -q | xargs -r docker rm && echo '✅ Old containers stopped' || echo '⚠️  No empatia containers found'"
echo ""

# 3. Prepare VPS directory
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Preparing VPS directory"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t $VPS_HOST "mkdir -p $VPS_BACKEND_DIR && echo '✅ Directory ready: $VPS_BACKEND_DIR'"
echo ""

# 4. Copy code
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Copying backend code (may take 30s)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
rsync -avz --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='deploy_*.sh' \
    "$LOCAL_BACKEND_DIR/" "$VPS_HOST:$VPS_BACKEND_DIR/"
echo ""
echo "✅ Code copied"
echo ""

# 5. Copy VPS-specific .env
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 5: Configuring environment for VPS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
scp "$LOCAL_BACKEND_DIR/.env.vps" "$VPS_HOST:$VPS_BACKEND_DIR/.env"
echo "✅ .env configured (PostgreSQL: localhost)"
echo ""

# 6. Build image
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 6: Building Docker image (may take 2-3 min)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t $VPS_HOST "cd $VPS_BACKEND_DIR && docker build -t empatia-backend:modular ."
echo ""

# 7. Start container
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 7: Starting new backend container"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t $VPS_HOST "cd $VPS_BACKEND_DIR && docker run -d \
    --name empatia-backend-modular \
    --restart unless-stopped \
    --network host \
    --env-file .env \
    -v $VPS_BACKEND_DIR/vertex-key.json:/app/vertex-key.json:ro \
    -v $VPS_BACKEND_DIR/logs:/app/logs \
    empatia-backend:modular && echo '✅ Container started: empatia-backend-modular'"
echo ""

# 8. Wait and check logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 8: Checking startup logs (waiting 5s)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
sleep 5
ssh -t $VPS_HOST "docker logs --tail 30 empatia-backend-modular"
echo ""

# 9. Final status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 9: Final status check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ssh -t $VPS_HOST "docker ps --filter 'name=empatia-backend-modular'"
echo ""

echo "========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================="
echo ""
echo "Backend URL: ws://72.60.89.5:8765"
echo ""
echo "Pipeline:"
echo "  STT:    Groq Whisper v3"
echo "  LLM:    Gemini 2.5 Flash Lite"
echo "  TTS:    Google WaveNet (pt-PT-Wavenet-D)"
echo "  Report: Gemini 2.0 Flash"
echo ""
echo "Next steps:"
echo "  1. Update frontend .env: NEXT_PUBLIC_WS_URL=ws://72.60.89.5:8765"
echo "  2. Test connection from frontend"
echo ""
echo "To view logs:"
echo "  ssh root@72.60.89.5"
echo "  docker logs -f empatia-backend-modular"
echo ""
