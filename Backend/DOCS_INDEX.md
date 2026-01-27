# 📚 Índice de Documentação - EmpatIA Backend

Guia rápido para navegar toda a documentação do projeto.

## 🎯 Começar Aqui

1. **[README.md](README.md)** - Visão geral do projeto e início rápido
2. **[requirements.txt](requirements.txt)** - Lista de dependências Python
3. **[.env.example](.env.example)** - Template de configuração

## 🚀 Setup e Instalação

- **[setup.sh](setup.sh)** - Script automático de instalação
- **[test_connection.py](test_connection.py)** - Teste de conectividade e configuração

## 📖 Documentação Técnica

### Para Desenvolvedores

| Documento | Descrição |
|-----------|-----------|
| [API_REFERENCE.md](API_REFERENCE.md) | Especificação completa da API WebSocket |
| [src/agent/system_prompt.py](src/agent/system_prompt.py) | System prompt do agente e contexto |
| [src/database/memory_store.py](src/database/memory_store.py) | Gestão de memórias do utilizador |
| [src/tools/](src/tools/) | Implementação das tools (manage_memory, google_search) |

### Para DevOps

| Documento | Descrição |
|-----------|-----------|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Guia completo de deployment na VPS |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Resolução de problemas comuns |

## 🏗️ Arquitetura do Código

```
Backend/
│
├── 📄 main.py                           # Ponto de entrada
├── 📄 test_connection.py                # Script de teste
├── 📄 requirements.txt                  # Dependências
├── 📄 .env.example                      # Template config
│
├── 📁 sql/
│   └── schema.sql                       # Schema PostgreSQL
│
└── 📁 src/
    │
    ├── 📁 config/
    │   ├── __init__.py
    │   └── settings.py                  # Configurações centralizadas
    │
    ├── 📁 database/
    │   ├── __init__.py
    │   ├── connection.py                # Pool PostgreSQL
    │   └── memory_store.py              # Gestão de memórias
    │
    ├── 📁 agent/
    │   ├── __init__.py
    │   ├── system_prompt.py             # System prompt dinâmico
    │   └── empatia_agent.py             # Agente principal ADK
    │
    ├── 📁 tools/
    │   ├── __init__.py
    │   ├── manage_memory.py             # Tool de memórias
    │   └── google_search.py             # Tool de pesquisa
    │
    └── 📁 server/
        ├── __init__.py
        └── websocket_server.py          # Servidor WebSocket
```

## 🔗 Links Rápidos por Tarefa

### "Como instalo o backend?"
👉 [README.md § Instalação](README.md#-instalação)  
👉 [setup.sh](setup.sh)

### "Como faço deploy na VPS?"
👉 [DEPLOYMENT.md](DEPLOYMENT.md)

### "Como conecto o frontend ao backend?"
👉 [API_REFERENCE.md](API_REFERENCE.md)

### "Como funciona a gestão de memórias?"
👉 [src/database/memory_store.py](src/database/memory_store.py)  
👉 [sql/schema.sql](sql/schema.sql)

### "Como adiciono uma nova tool?"
👉 [src/tools/manage_memory.py](src/tools/manage_memory.py) (exemplo)  
👉 [src/agent/empatia_agent.py](src/agent/empatia_agent.py) (integração)

### "O sistema não funciona, o que faço?"
👉 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)  
👉 [test_connection.py](test_connection.py)

### "Como customizo o comportamento do agente?"
👉 [src/agent/system_prompt.py](src/agent/system_prompt.py)  
👉 [.env.example](.env.example) (configuração de voz, temperatura, etc.)

## 📊 Fluxograma de Decisão

```
Preciso de...
│
├─ Instalar o sistema?
│  └─> README.md → setup.sh
│
├─ Fazer deploy?
│  └─> DEPLOYMENT.md
│
├─ Resolver problema?
│  └─> TROUBLESHOOTING.md → test_connection.py
│
├─ Integrar com frontend?
│  └─> API_REFERENCE.md
│
├─ Entender o código?
│  └─> src/ (explorar diretórios)
│
└─ Modificar comportamento?
   └─> system_prompt.py + .env
```

## 🔍 Pesquisa por Tópico

### PostgreSQL / Base de Dados
- [sql/schema.sql](sql/schema.sql)
- [src/database/connection.py](src/database/connection.py)
- [src/database/memory_store.py](src/database/memory_store.py)
- [TROUBLESHOOTING.md § PostgreSQL](TROUBLESHOOTING.md#postgresql-connection-refused)

### Google Gemini / ADK
- [src/agent/empatia_agent.py](src/agent/empatia_agent.py)
- [requirements.txt](requirements.txt)
- [TROUBLESHOOTING.md § Google API](TROUBLESHOOTING.md#-problemas-com-google-api)

### WebSocket / Streaming
- [src/server/websocket_server.py](src/server/websocket_server.py)
- [API_REFERENCE.md](API_REFERENCE.md)
- [TROUBLESHOOTING.md § WebSocket](TROUBLESHOOTING.md#-problemas-com-websocket)

### Áudio
- [API_REFERENCE.md § Audio Stream](API_REFERENCE.md#1-audio-stream-binary)
- [TROUBLESHOOTING.md § Áudio](TROUBLESHOOTING.md#-problemas-de-áudio)

### Tools / Ferramentas
- [src/tools/manage_memory.py](src/tools/manage_memory.py)
- [src/tools/google_search.py](src/tools/google_search.py)
- [TROUBLESHOOTING.md § Tools](TROUBLESHOOTING.md#-problemas-com-tools)

### Deployment / Produção
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [setup.sh](setup.sh)
- [test_connection.py](test_connection.py)

## 📞 Suporte

**Ordem de consulta recomendada:**

1. ✅ [README.md](README.md) - Visão geral
2. ✅ [test_connection.py](test_connection.py) - Verificar setup
3. ✅ [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Problemas comuns
4. ✅ Logs: `/var/log/empatia/` ou `sudo supervisorctl tail empatia`
5. 📧 Contactar equipa de desenvolvimento

---

**Versão:** 1.0.0  
**Última Atualização:** 2024-01-26  
**Projeto:** EmpatIA - Assistente Virtual Empática para Idosos
