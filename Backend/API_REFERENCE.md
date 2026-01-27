# EmpatIA Backend - API Reference

Documentação técnica da API WebSocket do EmpatIA.

## 🔌 Endpoint WebSocket

```
ws://host:port/ws?user_id={USER_ID}
```

### Parâmetros de Query

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `user_id` | string | Sim | Identificador único do utilizador |

### Exemplo de Conexão

```javascript
const ws = new WebSocket('ws://localhost:8765/ws?user_id=user_123');
```

## 📡 Protocolo de Comunicação

A comunicação segue um protocolo bidireccional com dois tipos de mensagens:

1. **Mensagens de Controlo** (JSON)
2. **Streams de Áudio** (Binary)

## 📤 Mensagens do Cliente → Servidor

### 1. Audio Stream (Binary)

Enviar chunks de áudio PCM raw:

**Formato:**
- **Codec**: PCM
- **Sample Rate**: 16kHz
- **Bit Depth**: 16-bit
- **Channels**: Mono (1 canal)
- **Byte Order**: Little-endian

**Exemplo (JavaScript):**

```javascript
// Usando Web Audio API
const audioContext = new AudioContext({ sampleRate: 16000 });
const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
const source = audioContext.createMediaStreamSource(mediaStream);

const processor = audioContext.createScriptProcessor(4096, 1, 1);
processor.onaudioprocess = (e) => {
    const inputData = e.inputBuffer.getChannelData(0);
    
    // Converter Float32Array para Int16Array (PCM 16-bit)
    const pcmData = new Int16Array(inputData.length);
    for (let i = 0; i < inputData.length; i++) {
        pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
    }
    
    // Enviar via WebSocket
    ws.send(pcmData.buffer);
};

source.connect(processor);
processor.connect(audioContext.destination);
```

### 2. Mensagens de Controlo (JSON)

#### Ping

Mantém a conexão viva.

```json
{
    "type": "ping"
}
```

**Resposta:**
```json
{
    "type": "pong"
}
```

#### End Session

Termina a sessão activa.

```json
{
    "type": "end_session"
}
```

## 📥 Mensagens do Servidor → Cliente

### 1. Audio Stream (Binary)

Chunks de áudio PCM da resposta do agente.

**Formato:** Idêntico ao formato de entrada (PCM 16kHz, 16-bit, mono).

**Exemplo (JavaScript):**

```javascript
ws.onmessage = (event) => {
    if (event.data instanceof Blob || event.data instanceof ArrayBuffer) {
        // Dados de áudio - reproduzir
        playAudioChunk(event.data);
    } else {
        // Mensagem JSON de controlo
        const message = JSON.parse(event.data);
        handleControlMessage(message);
    }
};

function playAudioChunk(audioData) {
    const audioContext = new AudioContext({ sampleRate: 16000 });
    
    // Converter ArrayBuffer para AudioBuffer
    const int16Array = new Int16Array(audioData);
    const float32Array = new Float32Array(int16Array.length);
    
    for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
    }
    
    const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
    audioBuffer.getChannelData(0).set(float32Array);
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();
}
```

### 2. Mensagens de Controlo (JSON)

#### Session Created

Enviada imediatamente após conexão bem-sucedida.

```json
{
    "type": "session_created",
    "session_id": "uuid-da-sessao",
    "user_id": "user_123"
}
```

#### Pong

Resposta ao ping.

```json
{
    "type": "pong"
}
```

## 🔄 Ciclo de Vida da Sessão

```
1. Cliente → Conecta ao WebSocket com user_id
2. Servidor → Envia "session_created"
3. Cliente ⇄ Servidor → Stream bidireccional de áudio
4. Cliente/Servidor → Pings periódicos para manter conexão
5. Cliente → Envia "end_session" ou desconecta
6. Servidor → Guarda episódio e limpa recursos
```

## 🛠️ Exemplo de Cliente Completo (JavaScript)

```javascript
class EmpatIAClient {
    constructor(userId, wsUrl = 'ws://localhost:8765') {
        this.userId = userId;
        this.wsUrl = `${wsUrl}/ws?user_id=${userId}`;
        this.ws = null;
        this.audioContext = null;
        this.sessionId = null;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                console.log('Conexão WebSocket estabelecida');
            };
            
            this.ws.onmessage = (event) => {
                if (typeof event.data === 'string') {
                    const message = JSON.parse(event.data);
                    
                    if (message.type === 'session_created') {
                        this.sessionId = message.session_id;
                        console.log('Sessão criada:', this.sessionId);
                        resolve();
                    }
                } else {
                    // Áudio binário
                    this.playAudio(event.data);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('Erro WebSocket:', error);
                reject(error);
            };
            
            this.ws.onclose = () => {
                console.log('Conexão WebSocket fechada');
                this.cleanup();
            };
        });
    }

    async startAudioStream() {
        this.audioContext = new AudioContext({ sampleRate: 16000 });
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = this.audioContext.createMediaStreamSource(stream);
        
        const processor = this.audioContext.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = this.convertToPCM(inputData);
                this.ws.send(pcmData.buffer);
            }
        };
        
        source.connect(processor);
        processor.connect(this.audioContext.destination);
    }

    convertToPCM(float32Array) {
        const pcmData = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return pcmData;
    }

    playAudio(audioData) {
        // Implementação de reprodução de áudio
        // (ver exemplo anterior)
    }

    endSession() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'end_session' }));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
        this.cleanup();
    }

    cleanup() {
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
}

// Uso
const client = new EmpatIAClient('user_123');
await client.connect();
await client.startAudioStream();

// Quando terminar
client.endSession();
client.disconnect();
```

## 🔐 Segurança

### Autenticação

Actualmente, a autenticação é feita via `user_id` no query parameter.

**Produção:** Implementar token-based authentication:

```javascript
const token = await getAuthToken();
const ws = new WebSocket(`ws://host:port/ws?token=${token}`);
```

### Rate Limiting

O servidor implementa:
- Ping/pong a cada 20 segundos
- Timeout de ping após 10 segundos
- Max message size: 10MB

### Encriptação

**Produção:** Use sempre WSS (WebSocket Secure):

```javascript
const ws = new WebSocket('wss://empatia.yourdomain.com/ws?user_id=123');
```

## 📊 Códigos de Erro WebSocket

| Código | Descrição |
|--------|-----------|
| 1000 | Normal closure |
| 1001 | Going away |
| 1008 | Policy violation (ex: user_id ausente) |
| 1011 | Internal server error |

## 🧪 Testar API

### Usando wscat

```bash
npm install -g wscat
wscat -c "ws://localhost:8765/ws?user_id=test_user"
```

### Usando Python

```python
import websockets
import asyncio

async def test():
    uri = "ws://localhost:8765/ws?user_id=test_user"
    async with websockets.connect(uri) as ws:
        # Enviar ping
        await ws.send('{"type": "ping"}')
        
        # Receber resposta
        response = await ws.recv()
        print(response)  # {"type": "pong"}

asyncio.run(test())
```

## 📈 Métricas e Monitorização

O backend regista eventos estruturados:

```json
{
    "event": "session_created",
    "user_id": "user_123",
    "session_id": "uuid",
    "timestamp": "2024-01-26T15:30:00Z"
}
```

**Eventos Monitorizados:**
- `session_created`: Nova sessão iniciada
- `session_ended`: Sessão terminada
- `tool_called`: Tool executada (manage_memory, google_search)
- `audio_chunk_sent`: Chunk de áudio enviado
- `error_occurred`: Erro na sessão

## 🔗 Integração com Frontend

Ver documentação do Frontend para exemplo de integração completa com React/Next.js.

---

**Versão da API**: 1.0.0  
**Última Atualização**: 2024-01-26
