/**
 * WebSocket Client para comunicação com o backend EmpatIA
 * Suporta streaming de áudio bidireccional
 */

export type WebSocketMessage =
  | { type: 'session_created'; session_id: string; user_id: string }
  | { type: 'pong' }
  | { type: 'error'; message: string };

export type WebSocketClientEvents = {
  open: () => void;
  close: (event: CloseEvent) => void;
  error: (error: Event) => void;
  message: (data: WebSocketMessage) => void;
  audioChunk: (audioData: ArrayBuffer) => void;
};

export class WebSocketClient {
  private ws: WebSocket | null = null;
  // eslint-disable-next-line @typescript-eslint/no-unsafe-function-type
  private listeners: Map<keyof WebSocketClientEvents, Set<Function>> = new Map();
  private url: string;
  private userId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(url: string, userId: string) {
    this.url = `${url}/ws?user_id=${userId}`;
    this.userId = userId;
  }

  /**
   * Conecta ao servidor WebSocket
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = () => {
          console.log('✅ WebSocket conectado');
          this.reconnectAttempts = 0;
          this.emit('open');
          resolve();
        };

        this.ws.onclose = (event) => {
          console.log('🔌 WebSocket desconectado', event.code, event.reason);
          this.emit('close', event);

          // Auto-reconnect se não foi fechado intencionalmente
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(
              `🔄 Tentativa de reconexão ${this.reconnectAttempts}/${this.maxReconnectAttempts}`
            );
            setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
          }
        };

        this.ws.onerror = (error) => {
          console.error('❌ Erro WebSocket:', error);
          this.emit('error', error);
          reject(error);
        };

        this.ws.onmessage = (event) => {
          if (typeof event.data === 'string') {
            // Mensagem JSON de controlo
            try {
              const message = JSON.parse(event.data) as WebSocketMessage;
              console.log('📨 Mensagem recebida:', message);
              this.emit('message', message);
            } catch (err) {
              console.error('Erro ao parsear mensagem JSON:', err);
            }
          } else if (event.data instanceof ArrayBuffer) {
            // Dados de áudio binários
            this.emit('audioChunk', event.data);
          }
        };
      } catch (error) {
        console.error('Erro ao criar WebSocket:', error);
        reject(error);
      }
    });
  }

  /**
   * Desconecta do servidor
   */
  disconnect(): void {
    if (this.ws) {
      this.reconnectAttempts = this.maxReconnectAttempts; // Prevenir auto-reconnect
      this.ws.close(1000, 'Desconexão intencional');
      this.ws = null;
    }
  }

  /**
   * Envia dados de áudio (PCM 16-bit)
   */
  sendAudio(audioData: ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(audioData);
    }
  }

  /**
   * Envia mensagem JSON de controlo
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  sendMessage(message: Record<string, any>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Verifica se está conectado
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Adiciona listener de evento
   */
  on<K extends keyof WebSocketClientEvents>(event: K, callback: WebSocketClientEvents[K]): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);
  }

  /**
   * Remove listener de evento
   */
  off<K extends keyof WebSocketClientEvents>(event: K, callback: WebSocketClientEvents[K]): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.delete(callback);
    }
  }

  /**
   * Emite evento para todos os listeners
   */
  private emit<K extends keyof WebSocketClientEvents>(
    event: K,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ...args: any[]
  ): void {
    const listeners = this.listeners.get(event);
    if (listeners) {
      listeners.forEach((callback) => {
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (callback as any)(...args);
        } catch (error) {
          console.error(`Erro no listener de ${event}:`, error);
        }
      });
    }
  }
}
