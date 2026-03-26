import type { App } from 'vue';
import { EventPulseClient, EventPulseOptions } from '../core';

export const EventPulsePlugin = {
  install(app: App, options: EventPulseOptions) {
    const client = new EventPulseClient(options);

    // Available in all components as this.$eventpulse
    app.config.globalProperties.$eventpulse = client;

    // Available via inject('eventpulse')
    app.provide('eventpulse', client);

    // Cleanup when app unmounts
    app.unmount = ((original) => () => {
      client.destroy();
      original();
    })(app.unmount);
  },
};