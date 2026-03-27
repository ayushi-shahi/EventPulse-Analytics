# Quick Start — React

## Step 1 — Install

```bash
npm install eventpulse-analytics
```

## Step 2 — Add the Provider

Wrap your app once in `main.jsx` (or `main.tsx`):

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { EventPulseProvider } from 'eventpulse-analytics'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <EventPulseProvider
    apiKey="ep_live_YOUR_KEY"
    endpoint="https://eventpulse-analytics-backend.onrender.com"
  >
    <App />
  </EventPulseProvider>
)
```

By default, `autoTrack={true}` — the provider will automatically track `page_view` on mount and `click` on interactive elements.

## Step 3 — Track Events in Components

```jsx
import { useEventPulse } from 'eventpulse-analytics'

export default function SignupButton() {
  const { track, identify } = useEventPulse()

  const handleClick = () => {
    try { identify('user_123') } catch {}
    track('signup_clicked', { plan: 'pro', source: 'hero' })
  }

  return <button onClick={handleClick}>Get Started</button>
}
```

> **Note:** Wrap `identify()` in a `try/catch` when calling it inside mutation callbacks or async handlers (e.g. after a login API call). This prevents a crash if the provider hasn't fully initialized at the time of the call:
>
> ```js
> try { identify(user.id) } catch {}
> ```

## Step 4 — Auto-Track Page Views (SPA)

Use `usePageView()` in route-level components to track navigation:

```jsx
import { usePageView } from 'eventpulse-analytics'

export default function PricingPage() {
  usePageView('/pricing')  // fires on mount
  return <div>...</div>
}
```

## Full API

### `useEventPulse()`

```js
const { track, identify, page } = useEventPulse()

track('event_name', { key: 'value' })   // custom event
identify('user_123')                     // associate user
page('/dashboard')                       // manual page view
```

### `<EventPulseProvider>` Props

| Prop              | Type        | Default  | Description                     |
| ----------------- | ----------- | -------- | ------------------------------- |
| `apiKey`        | `string`  | required | Your `ep_live_*` key          |
| `endpoint`      | `string`  | required | Backend URL                     |
| `batchInterval` | `number`  | `5000` | Flush interval in ms            |
| `autoTrack`     | `boolean` | `true` | Auto page view + click tracking |

## Verify It's Working

Open your EventPulse dashboard → **Live Feed** — events appear within 5 seconds.
