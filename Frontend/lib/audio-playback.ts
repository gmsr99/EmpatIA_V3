/**
 * Audio Playback Manager
 * Reproduz áudio PCM 16-bit 24kHz recebido do Gemini Live API
 */

export class AudioPlaybackManager {
  private audioContext: AudioContext | null = null;
  private queue: AudioBuffer[] = [];
  private isPlaying = false;
  private currentSource: AudioBufferSourceNode | null = null;
  // Gemini Live API retorna áudio PCM 16-bit a 24kHz
  private sampleRate = 24000;
  private destination: MediaStreamAudioDestinationNode | null = null;
  private outputStream: MediaStream | null = null;

  /**
   * Inicializa o contexto de áudio
   */
  async initialize(): Promise<void> {
    if (!this.audioContext) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.sampleRate,
      });

      // Criar destination para visualização
      this.destination = this.audioContext.createMediaStreamDestination();
      this.outputStream = this.destination.stream;
    }

    // Resume contexto se estiver suspenso
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
  }

  /**
   * Obtém o MediaStream do áudio de saída (para visualização)
   */
  getOutputStream(): MediaStream | null {
    return this.outputStream;
  }

  /**
   * Adiciona chunk de áudio à queue e reproduz
   */
  async playAudioChunk(audioData: ArrayBuffer): Promise<void> {
    if (!this.audioContext) {
      console.warn('AudioContext não inicializado');
      return;
    }

    try {
      // Converter ArrayBuffer (PCM Int16) para Float32Array
      const int16Array = new Int16Array(audioData);
      const float32Array = new Float32Array(int16Array.length);

      // Normalizar Int16 (-32768 a 32767) para Float32 (-1.0 a 1.0)
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      // Criar AudioBuffer
      const audioBuffer = this.audioContext.createBuffer(
        1, // Mono
        float32Array.length,
        this.sampleRate
      );

      audioBuffer.getChannelData(0).set(float32Array);

      // Adicionar à queue
      this.queue.push(audioBuffer);

      // Iniciar reprodução se não estiver a tocar
      if (!this.isPlaying) {
        this.playNext();
      }
    } catch (error) {
      console.error('Erro ao processar chunk de áudio:', error);
    }
  }

  /**
   * Reproduz o próximo buffer da queue
   */
  private playNext(): void {
    if (!this.audioContext || this.queue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const buffer = this.queue.shift()!;

    // Criar source node
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;

    // Conectar aos speakers E ao destination para visualização
    source.connect(this.audioContext.destination);
    if (this.destination) {
      source.connect(this.destination);
    }

    // Quando terminar, tocar o próximo
    source.onended = () => {
      this.currentSource = null;
      if (this.queue.length > 0) {
        this.playNext();
      } else {
        this.isPlaying = false;
      }
    };

    // Guardar referência e iniciar
    this.currentSource = source;
    source.start(0);
  }

  /**
   * Para a reprodução e limpa a queue
   */
  stop(): void {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
        this.currentSource.disconnect();
      } catch {
        // Ignorar erros se já foi parado
      }
      this.currentSource = null;
    }

    this.queue = [];
    this.isPlaying = false;
  }

  /**
   * Verifica se está a reproduzir áudio
   */
  getIsPlaying(): boolean {
    return this.isPlaying;
  }

  /**
   * Limpa recursos
   */
  async cleanup(): Promise<void> {
    this.stop();

    this.destination = null;
    this.outputStream = null;

    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }
  }
}
