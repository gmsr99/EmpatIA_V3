# EmpatIA Backend

Backend do agente de voz EmpatIA - Assistente virtual empática para combater a solidão em idosos em Portugal.

## 🎯 Características

- **Streaming de Áudio Bidireccional**: WebSocket para comunicação de voz em tempo real
- **Google Gemini Live**: Modelo `gemini-2.0-flash-exp` com voz nativa portuguesa (Kore)
- **Memória Persistente**: PostgreSQL com pgvector para busca semântica de memórias do utilizador
- **Ferramentas**:
  - `manage_memory`: Gestão silenciosa de memórias (família, saúde, hobbies, interesses)
  - `google_search`: Pesquisa Google para ancoragem em factos actuais
- **Português de Portugal**: Linguagem, cultura e tradições portuguesas

## 📋 Requisitos

- Python 3.10+
- PostgreSQL 14+ com extensão pgvector
- Google Cloud Project com Vertex AI habilitado
- Service Account Key do Google Cloud (vertex-key.json)

## 🚀 Instalação

### 1. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciais Google Cloud

Coloque o ficheiro de service account (`vertex-key.json`) na raiz do projeto Backend.

### 4. Configurar variáveis de ambiente

Copie o ficheiro `.env.example` para `.env`:

```bash
cp .env.example .env
```

O ficheiro `.env` já está configurado com:

```env
GOOGLE_APPLICATION_CREDENTIALS=vertex-key.json
GOOGLE_CLOUD_PROJECT=empatia-480916
GOOGLE_CLOUD_REGION=europe-southwest1

POSTGRES_HOST=72.60.89.5
POSTGRES_PORT=5433
POSTGRES_DB=bd_vet_empatia3
POSTGRES_USER=postgres
POSTGRES_PASSWORD=bigmoneycoming
```

### 5. Testar configuração

Execute o script de teste para verificar conectividade:

```bash
python test_connection.py
```

Este script verifica:
- Conexão ao PostgreSQL
- Extensão pgvector
- Tabelas do schema
- Autenticação Vertex AI

### 6. Inicializar base de dados

O schema SQL será aplicado automaticamente na primeira execução.

Ou pode aplicar manualmente:

```bash
psql -h 72.60.89.5 -p 5433 -U postgres -d bd_vet_empatia3 -f sql/schema.sql
```

## ▶️ Execução

### Iniciar o servidor

```bash
python main.py
```

O servidor WebSocket ficará disponível em:
```
ws://0.0.0.0:8765
```

### Conectar cliente

Os clientes devem conectar via WebSocket com o parâmetro `user_id`:

```
ws://host:8765/ws?user_id=USER_ID
```

## 🏗️ Arquitetura

```
Backend/
├── main.py                    # Ponto de entrada
├── requirements.txt           # Dependências Python
├── .env.example              # Template de variáveis de ambiente
│
├── sql/
│   └── schema.sql            # Schema PostgreSQL com pgvector
│
└── src/
    ├── config/
    │   └── settings.py       # Configurações centralizadas
    │
    ├── database/
    │   ├── connection.py     # Pool de conexões PostgreSQL
    │   └── memory_store.py   # Gestão de memórias do utilizador
    │
    ├── agent/
    │   ├── system_prompt.py  # System prompt dinâmico
    │   └── empatia_agent.py  # Agente principal com ADK
    │
    ├── tools/
    │   ├── manage_memory.py  # Tool de gestão de memórias
    │   └── google_search.py  # Tool de pesquisa Google
    │
    └── server/
        └── websocket_server.py  # Servidor WebSocket
```

## 🔧 Estrutura da Base de Dados

### Tabelas Principais

**user_profiles**
- Perfis dos utilizadores do sistema

**user_memories**
- Memórias do utilizador com embeddings para busca semântica
- Categorias: familia, saude, hobbies, interesses, geral
- Suporte a soft delete (is_active)

**conversation_episodes**
- Histórico de episódios de conversa
- Resumos, tópicos e tom emocional

## 🎙️ Protocolo WebSocket

### Mensagens do Cliente → Servidor

**Áudio (bytes)**
```
Enviar chunks de áudio PCM raw (16-bit, 16kHz)
```

**Controlo (JSON)**
```json
{
  "type": "ping"
}

{
  "type": "end_session"
}
```

### Mensagens do Servidor → Cliente

**Áudio (bytes)**
```
Chunks de áudio PCM da resposta do agente
```

**Controlo (JSON)**
```json
{
  "type": "session_created",
  "session_id": "uuid",
  "user_id": "user_id"
}

{
  "type": "pong"
}
```

## 🛠️ Ferramentas do Agente

### manage_memory

Gestão silenciosa de memórias do utilizador.

**Acções:**
- `ADD`: Adicionar nova memória
- `UPDATE`: Atualizar memória existente
- `DELETE`: Eliminar memória (soft delete)
- `SEARCH`: Buscar memórias semanticamente

**Categorias:**
- `familia`: Cônjuges, filhos, netos, família
- `saude`: Doenças, medicamentos, consultas
- `hobbies`: Atividades de lazer
- `interesses`: Tópicos de interesse
- `geral`: Outras informações

### google_search

Pesquisa Google para ancoragem factual.

**Uso:**
- Notícias actuais de Portugal
- Meteorologia
- Verificação de factos históricos
- Eventos e tradições

## 🌍 Configuração Regional

- **Idioma**: Português Europeu (pt-PT) rigoroso
- **Voz**: Kore (feminina, acolhedora)
- **Fuso horário**: Europe/Lisbon
- **Cultura**: Tradições, culinária e eventos portugueses

## 📝 Logs

O sistema usa `structlog` para logging estruturado:

```python
logger.info("Evento", key="value", user_id="123")
```

## 🔒 Segurança

- Credenciais em variáveis de ambiente (nunca no código)
- Conexões PostgreSQL com pool gerido
- WebSocket com ping/pong para manter conexões vivas
- Validação de input com Pydantic

## 🐛 Debugging

### Verificar conexão PostgreSQL

```bash
psql -h 72.60.89.5 -p 5433 -U postgres -d bd_vet_empatia3
```

### Verificar extensão pgvector

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Testar WebSocket

```bash
# Usando wscat
wscat -c "ws://localhost:8765/ws?user_id=test_user"
```

## 📚 Dependências Principais

- `google-genai`: Google Gemini API e ADK
- `asyncpg`: Cliente PostgreSQL assíncrono
- `pgvector`: Extensão para embeddings vectoriais
- `websockets`: Servidor WebSocket
- `pydantic`: Validação de dados
- `structlog`: Logging estruturado

## 🤝 Suporte

Para questões ou problemas:
1. Verificar logs do servidor
2. Validar credenciais no `.env`
3. Confirmar conectividade com PostgreSQL
4. Verificar quota da Google API

## 📄 Licença

Propriedade da Boommakers, Portugal.
