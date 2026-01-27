# EmpatIA Backend - Troubleshooting

Guia de resolução de problemas comuns.

## 🔍 Problemas de Conexão

### PostgreSQL Connection Refused

**Sintomas:**
```
asyncpg.exceptions.ConnectionDoesNotExistError
```

**Soluções:**

1. **Verificar se PostgreSQL está a correr:**
```bash
sudo systemctl status postgresql
```

2. **Testar conexão manualmente:**
```bash
psql -h 72.60.89.5 -p 5433 -U postgres -d bd_vet_empatia3
```

3. **Verificar firewall:**
```bash
# Na VPS do PostgreSQL
sudo ufw status
sudo ufw allow 5433/tcp
```

4. **Verificar pg_hba.conf:**
```bash
# Adicionar linha para permitir conexões remotas
host    all             all             0.0.0.0/0               md5
```

### pgvector Extension Not Found

**Sintomas:**
```
ERROR: type "vector" does not exist
```

**Solução:**
```bash
# Conectar ao PostgreSQL
psql -h 72.60.89.5 -p 5433 -U postgres -d bd_vet_empatia3

# Criar extensão
CREATE EXTENSION IF NOT EXISTS vector;

# Verificar
\dx
```

## 🔧 Problemas com Google API

### Invalid API Key

**Sintomas:**
```
google.api_core.exceptions.PermissionDenied: 403 API key not valid
```

**Soluções:**

1. **Verificar API key no .env:**
```bash
cat .env | grep GOOGLE_API_KEY
```

2. **Regenerar API key:**
   - Ir para [Google AI Studio](https://aistudio.google.com/apikey)
   - Criar nova chave
   - Atualizar `.env`

3. **Verificar serviços habilitados:**
   - Gemini API deve estar ativada no projeto Google Cloud

### Quota Exceeded

**Sintomas:**
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Soluções:**

1. **Ver quota atual:**
   - [Google Cloud Console → Quotas](https://console.cloud.google.com/iam-admin/quotas)

2. **Solicitar aumento de quota:**
   - Na consola, pedir aumento de quota para Gemini API

3. **Implementar rate limiting no cliente**

### Model Not Available

**Sintomas:**
```
google.api_core.exceptions.NotFound: 404 Model not found
```

**Solução:**

Verificar nome do modelo no `.env`:
```env
# Modelos disponíveis (Jan 2024):
GEMINI_MODEL=gemini-live-2.5-flash-native-audio
# ou
GEMINI_MODEL=gemini-live-2.5-flash-native-audio
```

## 🎙️ Problemas de Áudio

### No Audio Output

**Sintomas:**
- Cliente recebe mensagens JSON mas não áudio
- Stream vazio

**Soluções:**

1. **Verificar configuração de voz:**
```python
# settings.py
gemini_voice: str = "Kore"  # Vozes válidas: Puck, Charon, Kore, Fenrir, Aoede
```

2. **Verificar formato de áudio:**
```python
# Cliente deve enviar PCM 16kHz, 16-bit, mono
# Servidor retorna no mesmo formato
```

3. **Ver logs do servidor:**
```bash
sudo tail -f /var/log/empatia/access.log
```

### Audio Distorted/Choppy

**Sintomas:**
- Áudio entrecortado ou distorcido

**Soluções:**

1. **Verificar sample rate:**
```javascript
// Cliente
const audioContext = new AudioContext({ sampleRate: 16000 });
```

2. **Aumentar buffer size:**
```javascript
// Cliente
const processor = audioContext.createScriptProcessor(8192, 1, 1);  // Aumentar de 4096
```

3. **Verificar largura de banda:**
```bash
# Na VPS
sudo apt install speedtest-cli
speedtest-cli
```

## 🌐 Problemas com WebSocket

### Connection Timeout

**Sintomas:**
```
websockets.exceptions.ConnectionClosed: code = 1006
```

**Soluções:**

1. **Verificar se servidor está a correr:**
```bash
sudo supervisorctl status empatia
sudo netstat -tlnp | grep 8765
```

2. **Verificar firewall:**
```bash
sudo ufw status
sudo ufw allow 8765/tcp
```

3. **Testar localmente:**
```bash
wscat -c "ws://localhost:8765/ws?user_id=test"
```

### WebSocket Closes Immediately

**Sintomas:**
- Conexão estabelece mas fecha imediatamente

**Soluções:**

1. **Verificar user_id:**
```javascript
// Deve incluir user_id no query param
const ws = new WebSocket('ws://host:8765/ws?user_id=USER_ID');
```

2. **Ver logs de erro:**
```bash
sudo supervisorctl tail empatia stderr
```

## 💾 Problemas de Memória

### High Memory Usage

**Sintomas:**
```bash
htop  # Mostra uso alto de memória
```

**Soluções:**

1. **Reduzir pool de conexões PostgreSQL:**
```python
# src/database/connection.py
max_size=5,  # Reduzir de 10 para 5
```

2. **Limitar sessões simultâneas:**
```python
# src/server/websocket_server.py
# Adicionar limitação de conexões
MAX_CONNECTIONS = 50
```

3. **Limpar sessões antigas:**
```python
# Adicionar limpeza periódica de sessões inativas
```

## 🐛 Problemas com Tools

### manage_memory Não Guarda

**Sintomas:**
- Tool executada mas dados não aparecem na BD

**Soluções:**

1. **Verificar embeddings:**
```bash
# Na BD
SELECT id, content, embedding FROM user_memories LIMIT 1;
```

2. **Ver logs da tool:**
```bash
grep "manage_memory" /var/log/empatia/access.log
```

3. **Testar manualmente:**
```python
from src.tools.manage_memory import manage_memory_tool, ManageMemoryInput

params = ManageMemoryInput(
    action="ADD",
    category="geral",
    entity_type="teste",
    content="Teste manual"
)

result = await manage_memory_tool(params, "test_user")
print(result)
```

### google_search Falha

**Sintomas:**
```
{'success': False, 'error': '...'}
```

**Soluções:**

1. **Verificar se grounding está disponível:**
```python
# Gemini com grounding precisa de modelo compatível
# Usar: gemini-2.0-flash-exp ou superior
```

2. **Usar fallback para pesquisa simples:**
```python
# Implementar fallback sem grounding se necessário
```

## 🔄 Problemas de Deployment

### Supervisor Service Won't Start

**Sintomas:**
```bash
sudo supervisorctl status empatia
# FATAL
```

**Soluções:**

1. **Ver logs detalhados:**
```bash
sudo supervisorctl tail empatia stderr
```

2. **Verificar paths no config:**
```bash
sudo nano /etc/supervisor/conf.d/empatia.conf
# Validar todos os paths
```

3. **Testar comando manualmente:**
```bash
cd /home/user/empatia-backend
source venv/bin/activate
python main.py
```

4. **Recarregar supervisor:**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart empatia
```

## 📊 Comandos Úteis de Debug

### Ver Estado do Sistema

```bash
# Status geral
sudo supervisorctl status

# Uso de recursos
htop

# Conexões de rede
sudo netstat -tlnp | grep python

# Processos Python
ps aux | grep python

# Espaço em disco
df -h

# Logs em tempo real
sudo tail -f /var/log/empatia/access.log
```

### Testar Componentes Individualmente

```bash
# Testar conexão PostgreSQL
python test_connection.py

# Testar import de módulos
python -c "from src.agent.empatia_agent import agent; print('OK')"

# Testar configuração
python -c "from src.config import settings; print(settings.postgres_dsn)"
```

### Reiniciar Tudo

```bash
# Parar serviço
sudo supervisorctl stop empatia

# Reiniciar PostgreSQL (se necessário)
sudo systemctl restart postgresql

# Limpar cache Python
find . -type d -name __pycache__ -exec rm -rf {} +

# Reiniciar serviço
sudo supervisorctl start empatia
```

## 🆘 Quando Tudo Falha

1. **Backup dos logs:**
```bash
tar -czf logs_backup_$(date +%Y%m%d).tar.gz /var/log/empatia/
```

2. **Reset completo:**
```bash
# Parar tudo
sudo supervisorctl stop empatia

# Limpar ambiente
cd /home/user/empatia-backend
rm -rf venv
rm -rf __pycache__
find . -type d -name __pycache__ -exec rm -rf {} +

# Reinstalar
bash setup.sh

# Reconfigurar
cp .env.backup .env

# Reiniciar
sudo supervisorctl start empatia
```

3. **Contactar suporte com:**
   - Logs: `/var/log/empatia/`
   - Configuração: `.env` (REMOVER PASSWORDS)
   - Output de: `python test_connection.py`
   - Versão do Python: `python3 --version`
   - Versão das deps: `pip freeze`

---

**Lembrete:** Sempre fazer backup antes de mudanças significativas!
