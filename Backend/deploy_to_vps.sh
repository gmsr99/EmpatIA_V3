#!/bin/bash
set -e

VPS_HOST="root@72.60.89.5"
VPS_BACKEND_DIR="/root/empatia_backend"
LOCAL_BACKEND_DIR="/Users/gmsr44/Desktop/EmpatIA/8. Website/1. Agente com ADK/3. EmpatIA V3/Backend"

echo "========================================="
echo "EmpatIA Backend - Deploy to VPS"
echo "========================================="
echo ""

# 1. Check running containers
echo "1. Checking running containers on VPS..."
ssh $VPS_HOST "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'"
echo ""

# 2. Stop old backend container
echo "2. Stopping old backend container..."
OLD_CONTAINER=$(ssh $VPS_HOST "docker ps --filter 'name=empatia' --format '{{.Names}}' | head -1")
if [ -n "$OLD_CONTAINER" ]; then
    echo "   Found container: $OLD_CONTAINER"
    ssh $VPS_HOST "docker stop $OLD_CONTAINER && docker rm $OLD_CONTAINER"
    echo "   ✅ Old container stopped and removed"
else
    echo "   No empatia container found"
fi
echo ""

# 3. Create/update backend directory on VPS
echo "3. Creating backend directory on VPS..."
ssh $VPS_HOST "mkdir -p $VPS_BACKEND_DIR"
echo "   ✅ Directory ready: $VPS_BACKEND_DIR"
echo ""

# 4. Copy new backend code to VPS
echo "4. Copying backend code to VPS..."
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    "$LOCAL_BACKEND_DIR/" "$VPS_HOST:$VPS_BACKEND_DIR/"
echo "   ✅ Code copied"
echo ""

# 5. Build new Docker image on VPS
echo "5. Building new Docker image..."
ssh $VPS_HOST "cd $VPS_BACKEND_DIR && docker build -t empatia-backend:latest ."
echo "   ✅ Image built"
echo ""

# 6. Start new container
echo "6. Starting new backend container..."
ssh $VPS_HOST "cd $VPS_BACKEND_DIR && docker run -d \
    --name empatia-backend-new \
    --restart unless-stopped \
    --network host \
    --env-file .env \
    -v $VPS_BACKEND_DIR/vertex-key.json:/app/vertex-key.json:ro \
    -v $VPS_BACKEND_DIR/logs:/app/logs \
    empatia-backend:latest"
echo "   ✅ Container started"
echo ""

# 7. Check logs
echo "7. Checking startup logs..."
sleep 3
ssh $VPS_HOST "docker logs --tail 50 empatia-backend-new"
echo ""

# 8. Verify it's running
echo "8. Verifying container status..."
ssh $VPS_HOST "docker ps --filter 'name=empatia-backend-new' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""

echo "========================================="
echo "✅ Deployment complete!"
echo "Backend running at: ws://72.60.89.5:8765"
echo "========================================="
