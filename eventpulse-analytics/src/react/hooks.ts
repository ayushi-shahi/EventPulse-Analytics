import { useEffect } from 'react';
import { useEventPulseContext } from './provider';

// Core hook — access the client directly
export function useEventPulse() {
  const { client } = useEventPulseContext();

  return {
    track: (eventName: string, properties?: Record<string, unknown>) =>
      client?.track(eventName, properties),
    identify: (userId: string) =>
      client?.identify(userId),
    page: (url?: string) =>
      client?.page(url),
  };
}

// Auto-tracks page view when the component mounts
export function usePageView(url?: string) {
  const { client } = useEventPulseContext();

  useEffect(() => {
    client?.page(url);
  }, [url]);
}