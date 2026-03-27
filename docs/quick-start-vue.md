# Quick Start — Vue 3

## Step 1 — Install

```bash
npm install eventpulse-analytics
```

## Step 2 — Register the Plugin

In `main.js` (or `main.ts`):

```js
import { createApp } from 'vue'
import { EventPulsePlugin } from 'eventpulse-analytics'
import App from './App.vue'

const app = createApp(App)

app.use(EventPulsePlugin, {
  apiKey: 'ep_live_YOUR_KEY',
  endpoint: 'https://eventpulse-analytics-backend.onrender.com',
})

app.mount('#app')
```

## Step 3 — Track Events in Components

### Composition API (`inject`)

```vue
<script setup>
import { inject } from 'vue'

const ep = inject('eventpulse')

function onSignup() {
  try { ep.identify('user_123') } catch {}
  ep.track('signup_clicked', { plan: 'pro' })
}
</script>

<template>
  <button @click="onSignup">Get Started</button>
</template>
```

### Options API (`this.$eventpulse`)

```js
export default {
  methods: {
    onSignup() {
      try { this.$eventpulse.identify('user_123') } catch {}
      this.$eventpulse.track('signup_clicked', { plan: 'pro' })
    }
  }
}
```

> **Note:** Wrap `identify()` in a `try/catch` when calling it inside async handlers or mutation callbacks. This prevents a crash if the plugin hasn't fully initialized at the time of the call:
>
> ```js
> try { ep.identify(userId) } catch {}
> ```

## Full API

```js
ep.track('event_name', { key: 'value' })  // custom event
ep.identify('user_123')                    // associate user
ep.page('https://yourapp.com/pricing')    // manual page view
ep.flush()                                 // force-send queue
```

## Verify It's Working

Open your EventPulse dashboard → **Live Feed** — events appear within 5 seconds.
