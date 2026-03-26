// Core
export { EventPulseClient } from './core';
export type { EventPulseOptions, EventPayload } from './core';

// React
export { EventPulseProvider, useEventPulseContext } from './react/provider';
export { useEventPulse, usePageView } from './react/hooks';

// Vue
export { EventPulsePlugin } from './vue/plugin';