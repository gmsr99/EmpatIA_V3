#!/bin/bash
# Configurar SSL/HTTPS com Nginx para WebSocket

set -e

echo "🔒 EmpatIA - Configurar SSL/HTTPS"
echo "=================================="

# Verificar se domínio foi fornecido
if [ -z "$1" ]; then
    echo "❌ Erro: Forneça o domínio"
    echo "Uso: ./setup_ssl.sh seu-dominio.com"
    exit 1
fi

DOMAIN=$1

echo "🌐 Domínio: $DOMAIN"
echo ""

# 1. Configurar Nginx reverse proxy
echo "📝 Configurando Nginx..."
sudo tee /etc/nginx/sites-available/empatia > /dev/null <<EOF
# EmpatIA WebSocket Server
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket timeouts
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF

# 2. Habilitar site
sudo ln -sf /etc/nginx/sites-available/empatia /etc/nginx/sites-enabled/

# 3. Testar configuração
echo "🧪 Testando configuração Nginx..."
sudo nginx -t

# 4. Recarregar Nginx
echo "🔄 Recarregando Nginx..."
sudo systemctl reload nginx

# 5. Obter certificado SSL com Let's Encrypt
echo "🔐 Obtendo certificado SSL..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN --redirect

echo ""
echo "✅ SSL configurado com sucesso!"
echo ""
echo "🌐 WebSocket agora disponível em: wss://$DOMAIN"
echo ""
echo "📝 Atualize o frontend com:"
echo "   NEXT_PUBLIC_WS_URL=wss://$DOMAIN"
echo ""
echo "🔄 Renovação automática SSL configurada (certbot renew)"
