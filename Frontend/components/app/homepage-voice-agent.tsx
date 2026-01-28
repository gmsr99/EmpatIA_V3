'use client';

import React, { useCallback, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { AlertCircle, Loader2, MessageCircle, Mic, MicOff, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useVoiceAgent } from '@/hooks/useVoiceAgent';
import { GlowingRingVisualizer } from './glowing-ring-visualizer';

export function HomepageVoiceAgent() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Use the voice agent hook
  // Use a fallback ID if session user ID is not available yet, though authentication check handles this
  const userId = session?.user?.email || 'anonymous-user';

  const {
    state,
    isConnected,
    isMicEnabled,
    error: agentError,
    outputStream,
    connect,
    disconnect,
    toggleMic,
  } = useVoiceAgent(userId);

  // Combine local error state with agent error
  const [localError, setLocalError] = useState<string | null>(null);
  const displayError = localError || agentError;

  const handleConnect = useCallback(async () => {
    console.log('[HomepageVoiceAgent] Iniciar Conversa clicked');
    if (status === 'unauthenticated') {
      console.log('[HomepageVoiceAgent] User unauthenticated, redirecting to login');
      router.push('/login');
      return;
    }
    setLocalError(null);
    try {
      await connect();
    } catch (e) {
      console.error('[HomepageVoiceAgent] Connect failed:', e);
    }
  }, [status, router, connect]);

  const handleDisconnect = useCallback(() => {
    disconnect();
  }, [disconnect]);

  const handleToggleMic = useCallback(() => {
    toggleMic();
  }, [toggleMic]);

  if (status === 'loading') {
    return <div className="text-white">A carregar...</div>;
  }

  if (status === 'unauthenticated') {
    return (
      <div className="flex flex-col items-center gap-4 text-white">
        <p>Precisa de entrar para falar com a EmpatIA.</p>
        <Button onClick={() => router.push('/login')}>Entrar na Conta</Button>
      </div>
    );
  }

  const containerClasses =
    'relative flex h-[400px] w-full max-w-md flex-col items-center justify-center overflow-hidden rounded-3xl border border-white/10 bg-black/40 shadow-2xl backdrop-blur-xl';

  if (isConnected) {
    return (
      <div className={containerClasses}>
        <div className="relative flex h-full w-full flex-col items-center justify-center p-8">
          {/* Connection Status Label */}
          <div className="text-brand-lilac absolute top-6 left-1/2 -translate-x-1/2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium tracking-wider uppercase backdrop-blur-md">
            {state === 'speaking'
              ? 'A falar...'
              : state === 'listening'
                ? 'A ouvir...'
                : 'Em chamada'}
          </div>

          <div className="relative flex w-full flex-1 items-center justify-center">
            {/* Pass the assistant's output stream to the visualizer */}
            <GlowingRingVisualizer
              stream={outputStream || undefined}
              height="300px"
              width="300px"
            />
          </div>

          {/* Controls */}
          <div className="absolute bottom-6 flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggleMic}
              className={`h-12 w-12 rounded-full border backdrop-blur-md transition-all ${
                isMicEnabled
                  ? 'border-white/20 bg-white/10 text-white hover:bg-white/20'
                  : 'border-red-500/50 bg-red-500/10 text-red-400 hover:bg-red-500/20'
              }`}
            >
              {isMicEnabled ? <Mic className="h-6 w-6" /> : <MicOff className="h-6 w-6" />}
            </Button>

            <Button
              variant="destructive"
              size="icon"
              className="h-12 w-12 rounded-full border border-red-500/50 bg-red-500/20 text-red-400 backdrop-blur-md hover:bg-red-500/30"
              onClick={handleDisconnect}
            >
              <X className="h-6 w-6" />
            </Button>
          </div>

          {displayError && (
            <div className="absolute top-4 right-4 left-4 z-50 flex flex-col gap-2 rounded-lg border border-red-500/50 bg-red-900/90 p-3 text-sm text-red-100 shadow-xl backdrop-blur-md">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{displayError}</span>
                <button
                  onClick={() => setLocalError(null)}
                  className="ml-auto opacity-70 hover:opacity-100"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      <div className="relative z-10 flex h-full w-full flex-col items-center justify-center gap-4 py-6">
        <div className="space-y-1 text-center">
          <div className="text-brand-lilac text-xs font-medium tracking-widest uppercase">
            Olá, {session?.user?.name?.split(' ')[0]}
          </div>
          <h3 className="font-heading text-xl text-white/90">Posso ajudar?</h3>
        </div>

        <div className="flex items-center justify-center">
          <GlowingRingVisualizer height="180px" width="180px" />
        </div>

        <div className="flex flex-col items-center gap-2">
          <Button
            onClick={handleConnect}
            disabled={state === 'connecting'}
            className="group text-brand-signature relative inline-flex h-11 items-center gap-2.5 overflow-hidden rounded-full bg-white px-6 text-sm font-semibold shadow-[0_0_20px_rgba(255,255,255,0.15)] transition-all hover:scale-105 hover:bg-white/90 disabled:opacity-70"
          >
            {state === 'connecting' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <MessageCircle className="h-4 w-4 transition-transform group-hover:rotate-12" />
            )}
            <span>{state === 'connecting' ? 'A Ligação...' : 'Conversar Agora'}</span>
          </Button>

          {displayError && (
            <p className="max-w-[250px] animate-pulse text-center text-xs text-red-400">
              {displayError}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
