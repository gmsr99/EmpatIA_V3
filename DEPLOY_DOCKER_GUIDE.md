# 🐳 Guia de Deploy com Docker - EmpatIA V3

## ✅ Pré-requisitos

- [x] VPS com Docker instalado
- [x] PostgreSQL rodando em container Docker
- [x] Acesso SSH à VPS (root@72.60.89.5)
- [x] `vertex-key.json` (credenciais Google Cloud)

---

## 📦 Estrutura Docker

```
Backend/
├── Dockerfile              ✅ Criado
├── docker-compose.yml      ✅ Criado
├── .dockerignore          ✅ Criado
├── .env                   ⚠️  Criar
└── vertex-key.json        ⚠️  Copiar
```

---

## 🚀 DEPLOY PASSO A PASSO

### 1️⃣ Conectar ao PostgreSQL Existente

Primeiro, descobrir a **rede** do container PostgreSQL:

```bash
ssh root@72.60.89.5

# Listar containers em execução
docker ps

# Descobrir rede do PostgreSQL
docker inspect <postgres-container-name> | grep NetworkMode
# ou
docker network ls
docker network inspect <network-name>
```

**Exemplo de saída:**
```
NETWORK ID     NAME                DRIVER
abc123def456   postgres_network    bridge
```

### 2️⃣ Atualizar docker-compose.yml

Editar `Backend/docker-compose.yml`:

```yaml
networks:
  empatia_network:
    external: true
    name: postgres_network  # ← Nome da rede do PostgreSQL
```

**OU** se não souber o nome da rede, usar host networking:

```yaml
services:
  empatia-backend:
    network_mode: host  # Usar rede do host
    # Remover seção 'ports:' se usar host mode
```

### 3️⃣ Verificar Variáveis de Ambiente

Editar `Backend/.env`:

```env
# PostgreSQL (verificar IP/porta se usar network_mode: host)
POSTGRES_HOST=postgres  # Nome do container OU 127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=bd_vet_empatia3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=bigmoneycoming

# Restante das configs...
```

**Dica:** Se PostgreSQL está num container chamado `postgres-empatia`, use:
```env
POSTGRES_HOST=postgres-empatia
```

### 4️⃣ Copiar Código para VPS

```bash
# No seu Mac:
cd "Desktop/EmpatIA/8. Website/1. Agente com ADK/3. EmpatIA V3/Backend"

# Copiar via rsync (melhor que scp)
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  -e ssh . root@72.60.89.5:/opt/empatia/
```

### 5️⃣ Copiar Credenciais Google Cloud

```bash
# Copiar vertex-key.json
scp vertex-key.json root@72.60.89.5:/opt/empatia/
```

### 6️⃣ Build e Deploy

```bash
# Na VPS:
ssh root@72.60.89.5
cd /opt/empatia

# Tornar script executável
chmod +x deploy/docker-deploy.sh

# Executar deploy
./deploy/docker-deploy.sh
```

**Ou manualmente:**

```bash
# Build
docker-compose build

# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f empatia-backend
```

### 7️⃣ Verificar se Está Rodando

```bash
# Status dos containers
docker-compose ps

# Logs em tempo real
docker-compose logs -f

# Testar WebSocket localmente
docker exec empatia-backend python -c "import socket; s=socket.socket(); s.connect(('localhost', 8765)); print('✅ WebSocket OK')"
```

---

## 🔒 Configurar SSL/HTTPS (Nginx Reverse Proxy)

### Opção A: Nginx no Host (Recomendado)

```bash
# Instalar nginx
apt update && apt install -y nginx certbot python3-certbot-nginx

# Criar config
nano /etc/nginx/sites-available/empatia
```

Conteúdo:
```nginx
server {
    listen 80;
    server_name empatia-api.seu-dominio.com;

    location / {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

```bash
# Habilitar site
ln -s /etc/nginx/sites-available/empatia /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Obter SSL
certbot --nginx -d empatia-api.seu-dominio.com
```

### Opção B: Usar Ngrok (Temporário)

```bash
# Instalar ngrok
snap install ngrok

# Expor porta 8765
ngrok http 8765

# Usar URL fornecida (ex: https://abc123.ngrok.io)
```

---

## 📊 Gestão do Container

### Comandos Úteis

```bash
# Ver logs
docker-compose logs -f empatia-backend

# Reiniciar
docker-compose restart empatia-backend

# Parar
docker-compose down

# Parar e remover tudo
docker-compose down -v

# Rebuild após mudanças
docker-compose build --no-cache
docker-compose up -d

# Ver recursos usados
docker stats empatia-backend

# Entrar no container
docker exec -it empatia-backend bash
```

### Atualizar Código

```bash
# 1. Copiar novo código (do Mac)
rsync -avz --exclude 'venv' -e ssh . root@72.60.89.5:/opt/empatia/

# 2. Na VPS: rebuild e restart
cd /opt/empatia
docker-compose build
docker-compose up -d
```

### Ver Health Status

```bash
docker inspect empatia-backend | grep -A 5 Health
```

---

## 🔍 Troubleshooting

### Container não inicia

```bash
# Ver logs de erro
docker-compose logs empatia-backend

# Problemas comuns:
# 1. .env mal configurado
# 2. vertex-key.json em falta
# 3. Não consegue conectar ao PostgreSQL
```

### Não conecta ao PostgreSQL

```bash
# Testar conexão do container
docker exec empatia-backend python -c "
import psycopg2
conn = psycopg2.connect(
    host='postgres',
    port=5433,
    user='postgres',
    password='bigmoneycoming',
    database='bd_vet_empatia3'
)
print('✅ PostgreSQL OK')
conn.close()
"
```

Se falhar, verificar:
1. `POSTGRES_HOST` no `.env` está correto?
2. Container pode resolver o hostname `postgres`?
3. Containers estão na mesma rede?

```bash
# Ver rede do backend
docker inspect empatia-backend | grep NetworkMode

# Ver rede do postgres
docker inspect <postgres-container> | grep NetworkMode

# Devem estar na mesma rede!
```

### WebSocket não responde

```bash
# Verificar se porta está aberta
netstat -tulpn | grep 8765

# Verificar firewall
ufw status
ufw allow 8765/tcp
```

---

## 🔥 Configuração de Firewall

```bash
# Permitir portas necessárias
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (nginx)
ufw allow 443/tcp   # HTTPS (nginx)
ufw allow 8765/tcp  # WebSocket (se não usar nginx)

# Ativar
ufw enable

# Status
ufw status verbose
```

---

## 📈 Monitorização

### Logs Persistentes

```bash
# Configurar rotação de logs
nano /etc/logrotate.d/empatia
```

Conteúdo:
```
/opt/empatia/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 empatia empatia
}
```

### Alertas (Opcional)

Usar `healthcheck` do Docker:

```bash
# Ver status de health
docker inspect empatia-backend --format='{{json .State.Health}}'

# Criar script de monitorização
nano /usr/local/bin/check-empatia.sh
```

```bash
#!/bin/bash
if ! docker inspect empatia-backend | grep -q '"Status":"healthy"'; then
    echo "EmpatIA backend unhealthy!" | mail -s "Alert" admin@seu-dominio.com
    docker-compose restart empatia-backend
fi
```

```bash
chmod +x /usr/local/bin/check-empatia.sh

# Adicionar ao cron (a cada 5 min)
crontab -e
*/5 * * * * /usr/local/bin/check-empatia.sh
```

---

## 🎯 Checklist Final

- [ ] Docker e docker-compose instalados
- [ ] Código copiado para `/opt/empatia`
- [ ] `.env` configurado corretamente
- [ ] `vertex-key.json` copiado
- [ ] Container backend rodando (`docker-compose ps`)
- [ ] Logs sem erros (`docker-compose logs`)
- [ ] Conecta ao PostgreSQL ✅
- [ ] WebSocket responde na porta 8765
- [ ] Nginx configurado (se usar)
- [ ] SSL/HTTPS funcionando (se usar domínio)
- [ ] Firewall configurado
- [ ] Frontend Vercel conecta ao backend

---

## 📞 Próximos Passos

1. ✅ Backend rodando em Docker
2. 🌐 Configurar domínio + SSL
3. 🚀 Deploy frontend no Vercel
4. 🧪 Testar conversa end-to-end
5. 📊 Configurar monitorização

---

**Tempo estimado**: 1-2 horas

**Vantagens do Docker**:
- ✅ Isolamento
- ✅ Reprodutível
- ✅ Fácil rollback
- ✅ Mesma config em dev e prod
- ✅ Health checks automáticos
