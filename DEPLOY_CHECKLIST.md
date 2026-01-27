# 📋 Checklist de Deploy - EmpatIA v3

## ✅ CONCLUÍDO

### Backend
- [x] Integração Gemini Live API funcional
- [x] WebSocket streaming bidirecional
- [x] PostgreSQL com pgvector
- [x] Sistema de memórias (ADD/UPDATE/DELETE/SEARCH)
- [x] Autenticação Vertex AI
- [x] Logging estruturado
- [x] Gestão de sessões
- [x] Google Search tool

### Frontend
- [x] UI/UX moderna e responsiva
- [x] Autenticação NextAuth
- [x] Captura e playback de áudio
- [x] Visualizador de áudio
- [x] Dashboard com memórias
- [x] Design system consistente

## ⚠️ NECESSÁRIO ANTES DO DEPLOY

### Backend (VPS)

#### 🔴 CRÍTICO
- [ ] **Re-habilitar schema initialization** (atualmente desabilitado)
  - Arquivo: `Backend/src/agent/empatia_agent.py:90`
  - Problema: Índice ivfflat bloqueia se houver dados
  - Solução: Criar schema apenas se não existir

- [ ] **Remover test_main.py do uso em produção**
  - Usar `main.py` com logging corrigido

- [ ] **Adicionar variável ENV para ambiente**
  - `ENV=production` vs `ENV=development`

- [ ] **Configurar CORS no WebSocket**
  - Permitir apenas domínio Vercel do frontend

- [ ] **Rate limiting**
  - Limitar conexões por IP/usuário

- [ ] **SSL/TLS para WebSocket**
  - `wss://` em vez de `ws://`
  - Configurar certificado (Let's Encrypt)

#### 🟡 IMPORTANTE
- [ ] **Logging para arquivo**
  - Rotação de logs diários
  - Manter últimos 7 dias

- [ ] **Monitorização**
  - Health check endpoint
  - Métricas de uso

- [ ] **Gestão de processos**
  - Usar `systemd` ou `supervisor`
  - Auto-restart em caso de crash

- [ ] **Backup automático PostgreSQL**
  - Cron job diário

- [ ] **Secrets management**
  - Não commitar `.env` com credenciais reais
  - Usar variáveis de ambiente do sistema

#### 🟢 MELHORIAS
- [ ] Adicionar testes unitários
- [ ] Documentação API
- [ ] Métricas de performance
- [ ] Cache Redis para embeddings

### Frontend (Vercel)

#### 🔴 CRÍTICO
- [ ] **Configurar variáveis de ambiente no Vercel**
  - `NEXT_PUBLIC_WS_URL=wss://seu-dominio-vps.com`
  - `AUTH_SECRET` (gerar novo segredo forte)
  - Credenciais PostgreSQL

- [ ] **HTTPS obrigatório**
  - Vercel fornece automaticamente
  - Testar microfone funciona em produção

- [ ] **Domínio customizado** (opcional)
  - Configurar DNS
  - Certificado SSL

#### 🟡 IMPORTANTE
- [ ] **Otimizar build**
  - Verificar bundle size
  - Lazy loading de componentes pesados

- [ ] **Error boundaries**
  - Capturar erros de componentes
  - Página de erro amigável

- [ ] **Analytics** (opcional)
  - Google Analytics ou similar

#### 🟢 MELHORIAS
- [ ] PWA (Progressive Web App)
- [ ] Service Worker para offline
- [ ] Notificações push

## 📦 ESTRUTURA DE PASTAS

### Backend - Está BEM organizado ✅
```
Backend/
├── src/
│   ├── agent/           # Agente EmpatIA
│   ├── database/        # PostgreSQL
│   ├── server/          # WebSocket
│   ├── tools/           # Google Search, Memórias
│   └── config.py        # Configurações
├── sql/                 # Schema SQL
├── main.py             # Entry point
└── requirements.txt    # Dependências
```

### Frontend - Está BOM ✅ (padrão Next.js 15)
```
Frontend/
├── app/                # App Router
├── components/         # Componentes reutilizáveis
├── hooks/             # Custom hooks
├── lib/               # Utilitários
└── public/            # Assets estáticos
```

## 🚀 ORDEM DE DEPLOY RECOMENDADA

1. **VPS Backend** (primeiro)
   - Configurar servidor
   - Deploy backend
   - Testar WebSocket
   - Configurar SSL/HTTPS

2. **Vercel Frontend** (depois)
   - Configurar variáveis de ambiente
   - Apontar para WebSocket da VPS
   - Deploy

## 🔧 COMANDOS ÚTEIS

### Backend (VPS)
```bash
# Instalar dependências
cd Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Executar em produção
python main.py

# Com systemd (recomendado)
sudo systemctl start empatia-backend
sudo systemctl enable empatia-backend  # Auto-start
```

### Frontend (Vercel)
```bash
# Build local (testar)
npm run build

# Deploy
git push origin main  # Vercel auto-deploy
```

## 📊 MÉTRICAS DE SUCESSO

- [ ] Backend inicia em < 10s
- [ ] Latência WebSocket < 100ms
- [ ] Tempo de resposta Gemini < 3s
- [ ] 99% uptime
- [ ] Zero crashes em 24h

## 🔐 SEGURANÇA

- [ ] Firewall configurado (apenas portas necessárias)
- [ ] SSH com chave (desabilitar password)
- [ ] PostgreSQL não exposto publicamente
- [ ] Variáveis sensíveis em env vars (não em código)
- [ ] HTTPS/WSS em produção
- [ ] Rate limiting ativo
- [ ] Input validation em todos endpoints

## 📝 NOTAS

- **PostgreSQL**: Já está na VPS (72.60.89.5:5433) ✅
- **Google Vertex AI**: Credenciais em `vertex-key.json` (não commitar!)
- **Região**: europe-southwest1 (Madrid) ✅
