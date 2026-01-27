'use client';

import { AnimatePresence, type HTMLMotionProps, motion } from 'motion/react';
import { ChatEntry } from '@/components/ui/chat-entry';

const MotionContainer = motion.create('div');
const MotionChatEntry = motion.create(ChatEntry);

const CONTAINER_MOTION_PROPS = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut' as const,
        duration: 0.3,
        staggerChildren: 0.1,
        staggerDirection: -1,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut' as const,
        duration: 0.3,
        staggerChildren: 0.1,
        staggerDirection: 1,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const MESSAGE_MOTION_PROPS = {
  variants: {
    hidden: {
      opacity: 0,
      translateY: 10,
    },
    visible: {
      opacity: 1,
      translateY: 0,
    },
  },
};

export interface ChatMessage {
  id: string;
  timestamp: number;
  message: string;
  isLocal: boolean;
  name?: string;
  hasBeenEdited?: boolean;
}

interface ChatTranscriptProps {
  hidden?: boolean;
  messages?: ChatMessage[];
}

export function ChatTranscript({
  hidden = false,
  messages = [],
  ...props
}: ChatTranscriptProps & Omit<HTMLMotionProps<'div'>, 'ref'>) {
  return (
    <AnimatePresence>
      {!hidden && (
        <MotionContainer {...CONTAINER_MOTION_PROPS} {...props}>
          {messages.map((msg) => {
            const locale = navigator?.language ?? 'en-US';
            const messageOrigin = msg.isLocal ? 'local' : 'remote';

            return (
              <MotionChatEntry
                key={msg.id}
                locale={locale}
                timestamp={msg.timestamp}
                message={msg.message}
                messageOrigin={messageOrigin}
                name={msg.name}
                hasBeenEdited={msg.hasBeenEdited}
                {...MESSAGE_MOTION_PROPS}
              />
            );
          })}
        </MotionContainer>
      )}
    </AnimatePresence>
  );
}
