'use client';

import React, { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';
import { Transcript } from '@/hooks/useVoiceAgent';

interface TranscriptBoxProps {
  transcripts: Transcript[];
  className?: string;
}

export function TranscriptBox({ transcripts, className = '' }: TranscriptBoxProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll para a última mensagem
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts]);

  return (
    <div
      className={`flex h-full flex-col overflow-hidden rounded-3xl border border-white/10 bg-black/40 shadow-2xl backdrop-blur-xl ${className}`}
    >
      {/* Header */}
      <div className="border-b border-white/10 px-6 py-4">
        <h3 className="text-sm font-semibold text-white/90">Transcrição</h3>
        <p className="text-xs text-white/40">Legendas da conversa</p>
      </div>

      {/* Transcripts */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        {transcripts.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-white/30">Aguardando conversa...</p>
          </div>
        ) : (
          transcripts.map((transcript, index) => (
            <div
              key={index}
              className={`flex gap-3 ${transcript.role === 'assistant' ? 'flex-row' : 'flex-row-reverse'}`}
            >
              {/* Avatar */}
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                  transcript.role === 'assistant'
                    ? 'bg-brand-signature/20 text-brand-signature'
                    : 'bg-white/10 text-white/60'
                }`}
              >
                {transcript.role === 'assistant' ? (
                  <Bot className="h-4 w-4" />
                ) : (
                  <User className="h-4 w-4" />
                )}
              </div>

              {/* Message bubble */}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                  transcript.role === 'assistant'
                    ? 'bg-white/5 text-white/90'
                    : 'bg-brand-signature/10 text-white/90'
                }`}
              >
                <p className="text-sm leading-relaxed">{transcript.text}</p>
                <span className="mt-1 block text-xs text-white/30">
                  {new Date(transcript.timestamp).toLocaleTimeString('pt-PT', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
