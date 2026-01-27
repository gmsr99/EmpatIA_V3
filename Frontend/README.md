# EmpatIA Frontend

Frontend React/Next.js para o EmpatIA - um agente de IA conversacional.

## Features

- Interface de voz para interagir com o agente
- Suporte para chat de texto
- Visualizador de audio
- Temas claro/escuro com detecao de preferencia do sistema
- Branding e cores customizaveis via configuracao

## Getting Started

```bash
pnpm install
pnpm dev
```

Abrir http://localhost:3000 no browser.

## Configuracao

Configurar as variaveis de ambiente em `.env.local` (copiar de `.env.example`):

```env
AUTH_SECRET=your_auth_secret
POSTGRES_HOST=your_postgres_host
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=your_postgres_db
```

Personalizar branding e features em [`app-config.ts`](./app-config.ts).
