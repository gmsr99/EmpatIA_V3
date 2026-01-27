# 🚀 Guia de Deploy - EmpatIA V3

## 📋 Pré-requisitos

- [ ] VPS Ubuntu 20.04+ com root access
- [ ] Domínio apontando para o IP da VPS (para SSL)
- [ ] PostgreSQL já instalado na VPS ✅
- [ ] Conta Vercel (gratuita)
- [ ] `vertex-key.json` (credenciais Google Cloud)

## 🔧 Deploy Backend (VPS)

### Passo 1: Conectar à VPS
```bash
ssh root@72.60.89.5
# Senha: 3f-O78sAL@e/?cDw,Q.D
```

### Passo 2: Copiar código para VPS
```bash
# No seu computador local:
cd "Desktop/EmpatIA/8. Website/1. Agente com ADK/3. EmpatIA V3/Backend"
rsync -avz -e ssh . root@72.60.89.5:/tmp/empatia-backend/
```

### Passo 3: Executar setup automático
```bash
# Na VPS:
cd /tmp/empatia-backend/deploy
chmod +x setup_vps.sh
./setup_vps.sh
```

### Passo 4: Configurar credenciais
```bash
# Editar .env
sudo nano /opt/empatia/.env

# Copiar vertex-key.json
sudo cp /caminho/para/vertex-key.json /opt/empatia/
sudo chown empatia:empatia /opt/empatia/vertex-key.json
```

### Passo 5: Iniciar serviço
```bash
sudo systemctl start empatia-backend
sudo systemctl status empatia-backend

# Ver logs em tempo real
sudo journalctl -u empatia-backend -f
```

### Passo 6: Configurar SSL (HTTPS/WSS)
```bash
# Se tiver domínio (exemplo: empatia-api.seu-dominio.com)
cd /tmp/empatia-backend/deploy
chmod +x setup_ssl.sh
./setup_ssl.sh empatia-api.seu-dominio.com
```

**Sem domínio?** Use Ngrok temporariamente:
```bash
# Instalar ngrok
snap install ngrok

# Expor WebSocket
ngrok http 8765

# Usar URL fornecida (ex: wss://abc123.ngrok.io)
```

## 🌐 Deploy Frontend (Vercel)

### Passo 1: Preparar repositório Git
```bash
cd "Desktop/EmpatIA/8. Website/1. Agente com ADK/3. EmpatIA V3/Frontend"

# Inicializar git (se ainda não tiver)
git init
git add .
git commit -m "Initial commit - EmpatIA V3"

# Criar repo no GitHub
# Depois:
git remote add origin https://github.com/SEU-USUARIO/empatia-frontend.git
git push -u origin main
```

### Passo 2: Importar no Vercel
1. Ir para https://vercel.com
2. "Import Project" → conectar GitHub
3. Selecionar repositório `empatia-frontend`
4. Framework: **Next.js** (auto-detectado)

### Passo 3: Configurar variáveis de ambiente
No Vercel Dashboard > Settings > Environment Variables:

```env
# WebSocket URL (usar o da VPS com SSL)
NEXT_PUBLIC_WS_URL=wss://empatia-api.seu-dominio.com

# Auth
AUTH_SECRET=gerar-novo-segredo-aqui-64-chars

# PostgreSQL (mesmo da VPS)
POSTGRES_HOST=72.60.89.5
POSTGRES_PORT=5433
POSTGRES_DB=bd_vet_empatia3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=bigmoneycoming
```

**Gerar AUTH_SECRET:**
```bash
openssl rand -base64 64
```

### Passo 4: Deploy
```bash
# Vercel faz deploy automático quando push para main
git push origin main

# Ou deploy manual:
npx vercel --prod
```

## ✅ Verificação

### Backend
```bash
# Testar WebSocket localmente
wscat -c ws://localhost:8765

# Testar via domínio (com SSL)
wscat -c wss://empatia-api.seu-dominio.com
```

### Frontend
1. Aceder ao URL Vercel (ex: `empatia.vercel.app`)
2. Fazer login
3. Clicar "Conversar Agora"
4. Verificar se áudio funciona (requer HTTPS ✅)

## 🔍 Troubleshooting

### Backend não inicia
```bash
# Ver logs detalhados
sudo journalctl -u empatia-backend -n 100

# Testar manualmente
cd /opt/empatia
source venv/bin/activate
python main.py
```

### Frontend não conecta ao WebSocket
- Verificar se URL do WebSocket está correto (`.env.local` do Vercel)
- Verificar se VPS firewall permite porta 8765 ou 443
- Verificar logs do backend quando conecta

### Microfone não funciona
- **Causa**: Frontend não está em HTTPS
- **Solução**: Vercel fornece HTTPS automático, mas verifique URL

### PostgreSQL connection error
- Verificar se credenciais estão corretas
- Verificar se PostgreSQL aceita conexões remotas
- Testar: `psql -h 72.60.89.5 -p 5433 -U postgres -d bd_vet_empatia3`

## 📊 Monitorização

### Logs Backend (VPS)
```bash
# Logs em tempo real
sudo journalctl -u empatia-backend -f

# Últimas 100 linhas
sudo journalctl -u empatia-backend -n 100

# Logs de hoje
sudo journalctl -u empatia-backend --since today
```

### Logs Frontend (Vercel)
- Dashboard Vercel > Project > Logs
- Runtime Logs mostram erros de servidor
- Build Logs mostram erros de compilação

## 🔄 Atualizações

### Backend
```bash
# Atualizar código
cd /opt/empatia
sudo -u empatia git pull  # se usar git

# Ou copiar novos arquivos
rsync -avz -e ssh ./Backend/ root@72.60.89.5:/opt/empatia/

# Reiniciar serviço
sudo systemctl restart empatia-backend
```

### Frontend
```bash
# Simplesmente push para git
git add .
git commit -m "Update features"
git push origin main

# Vercel faz deploy automático
```

## 🔐 Segurança

### Backend
- [x] Firewall (UFW) configurado
- [x] SSL/TLS para WebSocket
- [ ] Rate limiting (TODO)
- [x] Variáveis sensíveis em .env

### Frontend
- [x] HTTPS (Vercel automático)
- [x] Auth com JWT
- [x] Env vars no Vercel (não no código)

## 💰 Custos Estimados

- **VPS**: Já tem ✅ (€0 adicional)
- **PostgreSQL**: Já tem ✅ (€0 adicional)
- **Vercel**: Grátis até 100GB bandwidth/mês ✅
- **Domínio**: ~€10/ano (opcional)
- **Google Vertex AI**: Pay-as-you-go (estimado ~€20-50/mês para uso moderado)

## 📞 Suporte

Se tiver problemas:
1. Verificar logs (backend e frontend)
2. Consultar este guia
3. Verificar DEPLOY_CHECKLIST.md
