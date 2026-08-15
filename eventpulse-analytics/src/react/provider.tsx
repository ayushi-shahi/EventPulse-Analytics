import { createContext, useContext, useEffect, useMemo, useState } from 'react';
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
  // State, not a ref.
  //
  // The client used to be created inside an effect and stored in a ref, then
  // read during render as `value={{ client: clientRef.current }}`. Assigning a
  // ref schedules no re-render, so the context kept the first render's value —
  // `{ client: null }` — forever. Every consumer of useEventPulse() therefore
  // called `client?.track(...)` on null and silently did nothing, while
  // auto-tracked page views still worked because the instance itself existed.
  const [client, setClient] = useState<EventPulseClient | null>(null);

  useEffect(() => {
    if (!apiKey || !endpoint) return;
    const instance = new EventPulseClient({ apiKey, endpoint, batchInterval, autoTrack });
    setClient(instance);
    return () => {
      instance.destroy();
      setClient(null);
    };
    // batchInterval / autoTrack are read once at construction; including them
    // would tear the client down and re-fire auto-tracked events.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, endpoint]);

  const value = useMemo(() => ({ client }), [client]);

  return (
    <EventPulseContext.Provider value={value}>
      {children}
    </EventPulseContext.Provider>
  );
}

export function useEventPulseContext() {
  return useContext(EventPulseContext);
}