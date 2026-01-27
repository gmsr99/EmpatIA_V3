#!/bin/bash
# Script de setup inicial para VPS (Ubuntu/Debian)

set -e  # Parar em caso de erro

echo "🚀 EmpatIA Backend - Setup VPS"
echo "================================"

# 1. Atualizar sistema
echo "📦 Atualizando sistema..."
sudo apt update && sudo apt upgrade -y

# 2. Instalar dependências
echo "📦 Instalando dependências do sistema..."
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# 3. Criar utilizador empatia (se não existir)
if ! id "empatia" &>/dev/null; then
    echo "👤 Criando utilizador empatia..."
    sudo useradd -m -s /bin/bash empatia
fi

# 4. Criar diretório da aplicação
echo "📁 Configurando diretórios..."
sudo mkdir -p /opt/empatia
sudo chown empatia:empatia /opt/empatia

# 5. Copiar arquivos (assumindo que está no diretório Backend/)
echo "📋 Copiando arquivos..."
sudo cp -r ../Backend/* /opt/empatia/
sudo chown -R empatia:empatia /opt/empatia

# 6. Criar ambiente virtual e instalar dependências Python
echo "🐍 Configurando ambiente Python..."
cd /opt/empatia
sudo -u empatia python3 -m venv venv
sudo -u empatia /opt/empatia/venv/bin/pip install --upgrade pip
sudo -u empatia /opt/empatia/venv/bin/pip install -r requirements.txt

# 7. Criar arquivo .env (você precisa editar manualmente depois!)
if [ ! -f /opt/empatia/.env ]; then
    echo "📝 Criando arquivo .env..."
    sudo -u empatia cp /opt/empatia/.env.example /opt/empatia/.env || echo "⚠️  .env.example não encontrado, crie manualmente!"
fi

# 8. Configurar systemd service
echo "⚙️  Configurando systemd service..."
sudo tee /etc/systemd/system/empatia-backend.service > /dev/null <<EOF
[Unit]
Description=EmpatIA Backend WebSocket Server
After=network.target postgresql.service

[Service]
Type=simple
User=empatia
WorkingDirectory=/opt/empatia
Environment="PATH=/opt/empatia/venv/bin"
ExecStart=/opt/empatia/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/empatia/backend.log
StandardError=append:/var/log/empatia/backend-error.log

[Install]
WantedBy=multi-user.target
EOF

# 9. Criar diretório de logs
sudo mkdir -p /var/log/empatia
sudo chown empatia:empatia /var/log/empatia

# 10. Recarregar systemd e habilitar serviço
echo "🔄 Habilitando serviço..."
sudo systemctl daemon-reload
sudo systemctl enable empatia-backend

# 11. Configurar firewall (UFW)
echo "🔥 Configurando firewall..."
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8765/tcp # WebSocket (temporário, depois via nginx reverse proxy)
sudo ufw --force enable

echo ""
echo "✅ Setup concluído!"
echo ""
echo "⚠️  PRÓXIMOS PASSOS MANUAIS:"
echo "1. Editar /opt/empatia/.env com suas credenciais"
echo "2. Copiar vertex-key.json para /opt/empatia/"
echo "3. Iniciar serviço: sudo systemctl start empatia-backend"
echo "4. Ver logs: sudo journalctl -u empatia-backend -f"
echo "5. Configurar SSL/HTTPS com nginx (ver setup_ssl.sh)"
