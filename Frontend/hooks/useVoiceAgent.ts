/**
 * Hook principal do Voice Agent EmpatIA
 * Orquestra WebSocket, captura de áudio e reprodução
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { WebSocketClient } from "@/lib/websocket-client";
import { AudioPlaybackManager } from "@/lib/audio-playback";

export type VoiceAgentState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "speaking"
  | "listening"
  | "error";

export interface UseVoiceAgentReturn {
  state: VoiceAgentState;
  isConnected: boolean;
  isMicEnabled: boolean;
  sessionId: string | null;
  error: string | null;
  micStream: MediaStream | null;
  outputStream: MediaStream | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  toggleMic: () => Promise<void>;
}

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8765";

export function useVoiceAgent(userId: string): UseVoiceAgentReturn {
  const [state, setState] = useState<VoiceAgentState>("disconnected");
  const [isMicEnabled, setIsMicEnabled] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [micStream, setMicStream] = useState<MediaStream | null>(null);
  const [outputStream, setOutputStream] = useState<MediaStream | null>(null);

  const wsClientRef = useRef<WebSocketClient | null>(null);
  const playbackManagerRef = useRef<AudioPlaybackManager | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);

  /**
   * Habilita captura de áudio do microfone
   */
  const enableMic = useCallback(async () => {
    try {
      console.log('[useVoiceAgent] Enabling microphone');

      // Verificar se a API de media devices está disponível
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const isSecure = window.location.protocol === 'https:' ||
                         window.location.hostname === 'localhost' ||
                         window.location.hostname === '127.0.0.1';

        if (!isSecure) {
          throw new Error(
            'O acesso ao microfone requer HTTPS. ' +
            'Aceda via http://localhost:3000 ou configure HTTPS.'
          );
        }
        throw new Error('O seu browser não suporta acesso ao microfone.');
      }

      console.log('[useVoiceAgent] A solicitar acesso ao microfone...');
      // Solicitar acesso ao microfone
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      console.log('[useVoiceAgent] ✅ Acesso ao microfone concedido');

      setMicStream(stream);

      console.log('[useVoiceAgent] A criar AudioContext...');
      // Criar AudioContext para processar áudio
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      console.log('[useVoiceAgent] ✅ AudioContext criado, state:', audioContext.state, 'sampleRate:', audioContext.sampleRate);

      // IMPORTANTE: Resume AudioContext se estiver suspended (alguns browsers exigem)
      if (audioContext.state === 'suspended') {
        console.log('[useVoiceAgent] AudioContext suspended, resuming...');
        await audioContext.resume();
        console.log('[useVoiceAgent] ✅ AudioContext resumed, new state:', audioContext.state);
      }

      const source = audioContext.createMediaStreamSource(stream);
      console.log('[useVoiceAgent] ✅ MediaStreamSource criado');

      // Usar ScriptProcessorNode para capturar áudio
      // (AudioWorklet seria melhor, mas requer mais setup)
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorNodeRef.current = processor;
      console.log('[useVoiceAgent] ✅ ScriptProcessorNode criado');

      let audioChunksSent = 0;
      let hasAudioCount = 0;
      processor.onaudioprocess = (e) => {
        if (!wsClientRef.current?.isConnected()) return;

        const inputData = e.inputBuffer.getChannelData(0);

        // Calcular nível RMS (Root Mean Square) do áudio
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        const hasAudio = rms > 0.01; // Threshold para detectar áudio real

        if (hasAudio) hasAudioCount++;

        // Converter Float32 para Int16 (PCM)
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Enviar ao backend
        try {
          wsClientRef.current.sendAudio(pcmData.buffer);
          audioChunksSent++;

          if (audioChunksSent === 1) {
            console.log('[useVoiceAgent] ✅ Primeiro chunk de áudio enviado');
          }
          if (audioChunksSent % 50 === 0) {
            console.log(`[useVoiceAgent] Enviados ${audioChunksSent} chunks - RMS: ${rms.toFixed(4)} - Com áudio: ${hasAudioCount}/${audioChunksSent}`);
          }
        } catch (err) {
          console.error('[useVoiceAgent] Erro ao enviar áudio:', err);
        }
      };

      console.log('[useVoiceAgent] A conectar source -> processor -> destination...');
      source.connect(processor);
      processor.connect(audioContext.destination);
      console.log('[useVoiceAgent] ✅ Pipeline de áudio conectado');

      setIsMicEnabled(true);
      setState("listening");
      console.log('[useVoiceAgent] ✅ Microfone habilitado com sucesso');
    } catch (err) {
      console.error("[useVoiceAgent] ❌ Erro ao habilitar microfone:", err);
      setError(`Falha ao aceder ao microfone: ${(err as Error)?.message || 'Erro desconhecido'}`);
      // NÃO desconectar aqui - deixar o usuário tentar novamente
    }
  }, []);

  /**
   * Conecta ao backend
   */
  const connect = useCallback(async () => {
    console.log('[useVoiceAgent] Connect called');
    try {
      setState("connecting");
      setError(null);

      // Criar WebSocket client
      console.log('[useVoiceAgent] Creating WebSocketClient with URL:', WS_URL);
      const wsClient = new WebSocketClient(WS_URL, userId);
      wsClientRef.current = wsClient;

      // Criar playback manager
      console.log('[useVoiceAgent] Initializing playback manager');
      const playbackManager = new AudioPlaybackManager();
      await playbackManager.initialize();
      playbackManagerRef.current = playbackManager;

      // Obter output stream para visualização
      const stream = playbackManager.getOutputStream();
      if (stream) {
        setOutputStream(stream);
        console.log('[useVoiceAgent] ✅ Output stream obtido para visualização');
      }

      // Setup listeners
      wsClient.on("open", () => {
        console.log("✅ [useVoiceAgent] Conectado ao backend");
        setState("connected");
      });

      wsClient.on("close", (event: CloseEvent) => {
        console.log("⚠️ [useVoiceAgent] WebSocket fechado", {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean
        });
        setState("disconnected");
        // NÃO chamar disconnect() aqui para evitar loop
        // disconnect();
      });

      wsClient.on("error", (err) => {
        console.error("❌ [useVoiceAgent] Erro WebSocket:", err);
        setError("Erro de conexão ao servidor");
        setState("error");
      });

      wsClient.on("message", (message) => {
        if (message.type === "session_created") {
          setSessionId(message.session_id);
          console.log("✅ [useVoiceAgent] Sessão criada:", message.session_id);
        }
      });

      wsClient.on("audioChunk", async (audioData) => {
        // Reproduzir áudio recebido do agente
        await playbackManager.playAudioChunk(audioData);

        // Atualizar estado para "speaking" quando recebe áudio
        setState((prevState) => {
          if (prevState !== "speaking") {
            return "speaking";
          }
          return prevState;
        });
      });

      // Conectar ao WebSocket
      console.log('[useVoiceAgent] Calling wsClient.connect()');
      await wsClient.connect();
      console.log('[useVoiceAgent] ✅ WebSocket connected successfully');

      // Pequena pausa para garantir que a conexão está estável
      await new Promise(resolve => setTimeout(resolve, 100));

      // Auto-enable mic após conexão
      if (wsClient.isConnected()) {
        console.log('[useVoiceAgent] Enabling microphone');
        await enableMic();
      } else {
        console.warn('[useVoiceAgent] WebSocket não está conectado, não habilitando microfone');
      }
    } catch (err) {
      console.error("❌ [useVoiceAgent] Erro fatal durante conexão:", err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError(`Falha ao conectar: ${(err as any)?.message || 'Erro desconhecido'}`);
      setState("error");
    }
  }, [userId, enableMic]);

  /**
   * Desconecta do backend
   */
  const disconnect = useCallback(() => {
    // Parar playback
    if (playbackManagerRef.current) {
      playbackManagerRef.current.cleanup();
      playbackManagerRef.current = null;
    }

    // Desconectar WebSocket
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
    }

    // Parar microfone
    if (micStream) {
      micStream.getTracks().forEach((track) => track.stop());
      setMicStream(null);
    }

    // Limpar output stream
    setOutputStream(null);

    // Limpar audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }

    setIsMicEnabled(false);
    setState("disconnected");
    setSessionId(null);
  }, [micStream]);

  /**
   * Desabilita captura de áudio
   */
  const disableMic = useCallback(() => {
    if (micStream) {
      micStream.getTracks().forEach((track) => track.stop());
      setMicStream(null);
    }

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    setIsMicEnabled(false);
    setState("connected");
  }, [micStream]);

  /**
   * Toggle microfone
   */
  const toggleMic = useCallback(async () => {
    if (isMicEnabled) {
      disableMic();
    } else {
      await enableMic();
    }
  }, [isMicEnabled, enableMic, disableMic]);

  // Cleanup ao desmontar
  useEffect(() => {
    return () => {
      console.log('[useVoiceAgent] Component unmounting, cleaning up...');
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - só executar no unmount

  return {
    state,
    isConnected: state === "connected" || state === "speaking" || state === "listening",
    isMicEnabled,
    sessionId,
    error,
    micStream,
    outputStream,
    connect,
    disconnect,
    toggleMic,
  };
}
