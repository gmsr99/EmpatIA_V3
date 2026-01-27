# EmpatIA Backend - Guia de Deployment

Este guia documenta o processo de deployment do backend EmpatIA na VPS.

## 📋 Pré-requisitos na VPS

### 1. Sistema Operativo
- Ubuntu 22.04 LTS ou superior
- Acesso SSH com privilégios sudo

### 2. Software Necessário

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# PostgreSQL com pgvector
# (Já instalado no servidor 72.60.89.5:5433)

# Git (opcional)
sudo apt install git -y

# Supervisor (para gestão do processo)
sudo apt install supervisor -y

# Nginx (para proxy reverso, opcional)
sudo apt install nginx -y
```

## 🚀 Deployment Passo-a-Passo

### 1. Transferir Código para VPS

```bash
# Via SCP
scp -r Backend/ user@vps-ip:/home/user/empatia-backend

# Ou via Git
ssh user@vps-ip
cd /home/user
git clone <repository-url> empatia-backend
cd empatia-backend
```

### 2. Configurar Ambiente

```bash
cd /home/user/empatia-backend

# Executar script de setup
bash setup.sh

# Ou manualmente:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env
```

Preencher com as credenciais reais:

```env
GOOGLE_API_KEY=<sua_key_aqui>
POSTGRES_HOST=72.60.89.5
POSTGRES_PORT=5433
POSTGRES_DB=bd_vet_empatia3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=bigmoneycoming
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
```

### 4. Inicializar Base de Dados

```bash
source venv/bin/activate
python test_connection.py
```

Se as tabelas não existirem:

```bash
python -c "from src.database.connection import DatabaseConnection; import asyncio; asyncio.run(DatabaseConnection.init_schema())"
```

### 5. Testar Localmente

```bash
python main.py
```

Se tudo correr bem, verá:

```
EmpatIA Backend PRONTO
WebSocket disponível em: ws://0.0.0.0:8765
```

Teste com `Ctrl+C` para parar.

## 🔧 Configurar como Serviço (Supervisor)

### 1. Criar Ficheiro de Configuração

```bash
sudo nano /etc/supervisor/conf.d/empatia.conf
```

Conteúdo:

```ini
[program:empatia]
directory=/home/user/empatia-backend
command=/home/user/empatia-backend/venv/bin/python main.py
user=user
autostart=true
autorestart=true
stderr_logfile=/var/log/empatia/error.log
stdout_logfile=/var/log/empatia/access.log
environment=PATH="/home/user/empatia-backend/venv/bin"

[eventlistener:empatia_crash]
command=/home/user/empatia-backend/venv/bin/python -m supervisord.events
events=PROCESS_STATE_FATAL
```

### 2. Criar Diretório de Logs

```bash
sudo mkdir -p /var/log/empatia
sudo chown user:user /var/log/empatia
```

### 3. Ativar e Iniciar Serviço

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start empatia
```

### 4. Verificar Status

```bash
sudo supervisorctl status empatia
```

### 5. Ver Logs

```bash
sudo tail -f /var/log/empatia/access.log
sudo tail -f /var/log/empatia/error.log
```

## 🌐 Configurar Nginx (Proxy Reverso)

### 1. Criar Configuração Nginx

```bash
sudo nano /etc/nginx/sites-available/empatia
```

Conteúdo:

```nginx
upstream empatia_backend {
    server 127.0.0.1:8765;
}

server {
    listen 80;
    server_name empatia.yourdomain.com;

    location /ws {
        proxy_pass http://empatia_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }

    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

### 2. Ativar Site

```bash
sudo ln -s /etc/nginx/sites-available/empatia /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 3. Certificado SSL (Opcional mas Recomendado)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d empatia.yourdomain.com
```

## 🔒 Segurança

### 1. Firewall

```bash
# Permitir SSH
sudo ufw allow 22/tcp

# Permitir HTTP/HTTPS (se usar Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Permitir WebSocket (se acesso direto)
sudo ufw allow 8765/tcp

# Ativar firewall
sudo ufw enable
```

### 2. Permissões

```bash
# Ficheiro .env deve ter permissões restritas
chmod 600 .env
```

### 3. Atualizações Automáticas

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

## 📊 Monitorização

### Ver Logs em Tempo Real

```bash
# Logs do supervisor
sudo tail -f /var/log/empatia/access.log

# Logs do nginx (se aplicável)
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Comandos Úteis do Supervisor

```bash
# Ver status
sudo supervisorctl status empatia

# Reiniciar
sudo supervisorctl restart empatia

# Parar
sudo supervisorctl stop empatia

# Iniciar
sudo supervisorctl start empatia

# Ver logs
sudo supervisorctl tail empatia
sudo supervisorctl tail -f empatia  # follow mode
```

## 🔄 Atualizações

### Atualizar Código

```bash
cd /home/user/empatia-backend

# Pull do git (se aplicável)
git pull

# Ou transferir ficheiros novos via SCP

# Ativar venv
source venv/bin/activate

# Atualizar dependências
pip install -r requirements.txt --upgrade

# Reiniciar serviço
sudo supervisorctl restart empatia
```

## 🐛 Troubleshooting

### Serviço Não Inicia

```bash
# Ver logs de erro
sudo supervisorctl tail empatia stderr

# Verificar configuração
python test_connection.py
```

### Erro de Conexão PostgreSQL

```bash
# Testar conexão manualmente
psql -h 72.60.89.5 -p 5433 -U postgres -d bd_vet_empatia3

# Verificar variáveis de ambiente
cat .env
```

### WebSocket Não Conecta

```bash
# Verificar se o serviço está a correr
sudo supervisorctl status empatia

# Verificar porta
sudo netstat -tlnp | grep 8765

# Testar localmente
pip install websocket-client
python -c "import websocket; ws = websocket.WebSocket(); ws.connect('ws://localhost:8765/ws?user_id=test'); print('OK'); ws.close()"
```

### Alta Utilização de Memória

```bash
# Ver uso de recursos
htop

# Ajustar pool de conexões PostgreSQL em settings.py
# max_size=10 -> reduzir se necessário
```

## 📝 Checklist de Deployment

- [ ] VPS configurada com Python 3.10+
- [ ] PostgreSQL acessível e pgvector instalado
- [ ] Código transferido para VPS
- [ ] Ambiente virtual criado
- [ ] Dependências instaladas
- [ ] `.env` configurado com credenciais
- [ ] Base de dados inicializada
- [ ] Teste de conexão bem-sucedido
- [ ] Supervisor configurado
- [ ] Serviço a correr automaticamente
- [ ] Logs a funcionar
- [ ] Firewall configurado
- [ ] (Opcional) Nginx configurado
- [ ] (Opcional) SSL ativado
- [ ] Monitorização ativa

## 🆘 Suporte

Em caso de problemas:

1. Verificar logs: `/var/log/empatia/`
2. Testar conectividade: `python test_connection.py`
3. Validar configuração: verificar `.env`
4. Reiniciar serviço: `sudo supervisorctl restart empatia`

---

**Notas:**
- Substituir `user` pelo username real na VPS
- Substituir `vps-ip` pelo IP real: `72.60.89.5`
- Substituir `yourdomain.com` pelo domínio real (se aplicável)
