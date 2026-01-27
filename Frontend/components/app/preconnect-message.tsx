'use client';

import { AnimatePresence, motion } from 'motion/react';
import { ShimmerText } from '@/components/ui/shimmer-text';
import { cn } from '@/lib/utils';

const MotionMessage = motion.create('p');

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn' as const,
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn' as const,
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface PreConnectMessageProps {
  hasMessages?: boolean;
  className?: string;
}

export function PreConnectMessage({ className, hasMessages = false }: PreConnectMessageProps) {
  return (
    <AnimatePresence>
      {!hasMessages && (
        <MotionMessage
          {...VIEW_MOTION_PROPS}
          aria-hidden={hasMessages}
          className={cn('pointer-events-none text-center', className)}
        >
          <ShimmerText className="text-sm font-semibold">
            Agent is listening, ask it a question
          </ShimmerText>
        </MotionMessage>
      )}
    </AnimatePresence>
  );
}
