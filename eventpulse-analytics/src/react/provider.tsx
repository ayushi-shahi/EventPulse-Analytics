import { createContext, useContext, useEffect, useRef } from 'react';
import { EventPulseClient, EventPulseOptions } from '../core';

interface EventPulseContextValue {
  client: EventPulseClient | null;
}

const EventPulseContext = createContext<EventPulseContextValue>({ client: null });

export function EventPulseProvider({
  children,
  apiKey,
  endpoint,
  batchInterval,
  autoTrack,
}: EventPulseOptions & { children: React.ReactNode }) {
  const clientRef = useRef<EventPulseClient | null>(null);

  useEffect(() => {
    clientRef.current = new EventPulseClient({ apiKey, endpoint, batchInterval, autoTrack });
    return () => clientRef.current?.destroy();
  }, [apiKey, endpoint]);

  return (
    <EventPulseContext.Provider value={{ client: clientRef.current }}>
      {children}
    </EventPulseContext.Provider>
  );
}

export function useEventPulseContext() {
  return useContext(EventPulseContext);
}