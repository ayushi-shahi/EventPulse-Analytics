# eventpulse-analytics

Official JavaScript/TypeScript SDK for [EventPulse Analytics](https://github.com/ayushi-shahi/EventPulse-Analytics).

Supports React, Vue 3, and plain JS/TS apps.

[![npm](https://img.shields.io/npm/v/eventpulse-analytics)](https://www.npmjs.com/package/eventpulse-analytics)

## Install

```bash
npm install eventpulse-analytics
```

---

## React

### 1. Wrap your app with `EventPulseProvider`

```jsx
import { EventPulseProvider } from "eventpulse-analytics";

export default function App() {
  return (
    <EventPulseProvider
      apiKey="ep_live_YOUR_KEY"
      endpoint="https://eventpulse-analytics-backend.onrender.com"
    >
      <YourApp />
    </EventPulseProvider>
  );
}
```

### 2. Track events with `useEventPulse`

```jsx
import { useEventPulse } from "eventpulse-analytics";

export default function SignupButton() {
  const { track, identify } = useEventPulse();

  return (
    <button onClick={() => {
      identify("user_123");
      track("signup", { plan: "pro" });
    }}>
      Sign Up
    </button>
  );
}
```

### 3. Auto-track page views with `usePageView`

```jsx
import { usePageView } from "eventpulse-analytics";

export default function PricingPage() {
  usePageView("/pricing");   // tracks on mount
  return <div>...</div>;
}
```

---

## Vue 3

### 1. Register the plugin

```js
import { createApp } from "vue";
import { EventPulsePlugin } from "eventpulse-analytics";
import App from "./App.vue";

const app = createApp(App);

app.use(EventPulsePlugin, {
  apiKey: "ep_live_YOUR_KEY",
  endpoint: "https://eventpulse-analytics-backend.onrender.com",
});

app.mount("#app");
```

### 2. Use in components

```vue
<script setup>
import { inject } from "vue";
const ep = inject("eventpulse");

function onSignup() {
  ep.identify("user_123");
  ep.track("signup", { plan: "pro" });
}
</script>
```

Or via `this.$eventpulse` in Options API:

```js
this.$eventpulse.track("button_click", { label: "Get Started" });
```

---

## Plain JS / TypeScript

```ts
import { EventPulseClient } from "eventpulse-analytics";

const client = new EventPulseClient({
  apiKey: "ep_live_YOUR_KEY",
  endpoint: "https://eventpulse-analytics-backend.onrender.com",
});

client.track("page_view", { url: window.location.href });
client.identify("user_123");
client.page("/dashboard");

// cleanup on app teardown
client.destroy();
```

---

## API Reference

### `EventPulseClient`

| Method                        | Description                     |
| ----------------------------- | ------------------------------- |
| `track(event, properties?)` | Track a custom event            |
| `identify(userId)`          | Associate events with a user    |
| `page(url?)`                | Track a page view               |
| `flush()`                   | Force-send queued events        |
| `destroy()`                 | Flush and stop background timer |

### `EventPulseProvider` props (React)

| Prop              | Default  | Description                    |
| ----------------- | -------- | ------------------------------ |
| `apiKey`        | required | Your `ep_live_*`key          |
| `endpoint`      | required | Backend URL                    |
| `batchInterval` | `5000` | Flush interval in ms           |
| `autoTrack`     | `true` | Auto-track page views & clicks |

---

## Drop-in Script (no npm)

```html
<script
  src="https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js"
  data-api-key="ep_live_YOUR_KEY">
</script>

<script>
  // manual tracking
  window.EventPulse.track("button_click", { label: "Hero CTA" });
  window.EventPulse.identify("user_123");
</script>
```

Auto-tracks `page_view` and `click` events out of the box, including SPA navigation (React Router, Vue Router, Next.js).

---

## Event Format

All events are sent to:

```
POST /api/v1/ingest/events/batch
X-API-Key: ep_live_YOUR_KEY
```

```json
{
  "events": [
    {
      "event_name": "signup",
      "user_id": "user_123",
      "properties": { "plan": "pro" },
      "timestamp": "2026-03-27T10:00:00.000Z"
    }
  ]
}
```
