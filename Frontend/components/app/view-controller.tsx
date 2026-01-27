'use client';

import { AnimatePresence, motion } from 'motion/react';
import type { AppConfig } from '@/app-config';
import { WelcomeView } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear' as const,
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  // TODO: Implement ADK session state management
  const isConnected = false;

  const handleStartCall = () => {
    // TODO: Implement ADK connection logic
    console.log('Starting call...');
  };

  return (
    <AnimatePresence mode="wait">
      {!isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
        />
      )}
      {/* TODO: Add session view when ADK is implemented */}
    </AnimatePresence>
  );
}
