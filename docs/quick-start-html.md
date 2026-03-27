# Quick Start — Plain HTML (Drop-in Script)

No install, no build step. Paste one `<script>` tag and you're done.

## Step 1 — Get an API Key

1. Open your EventPulse dashboard
2. Go to **API Keys** → **Create New Key**
3. Copy your `ep_live_...` key

## Step 2 — Add the Script

Paste this just before `</body>` in your HTML:

```html
<script
  src="https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js"
  data-api-key="ep_live_YOUR_KEY">
</script>
```

That's it. The SDK will automatically track:

* `page_view` on every page load
* `click` on every button, link, and `data-track` element
* SPA navigation (React Router, Vue Router, Next.js)

## Step 3 — Manual Tracking (Optional)

```html
<script>
  // Track a custom event
  window.EventPulse.track("signup_clicked", { plan: "pro" });

  // Associate events with a user
  window.EventPulse.identify("user_123");

  // Force-send queued events immediately
  window.EventPulse.flush();
</script>
```

## What Gets Tracked Automatically

Every event includes these base properties:

| Property       | Example                          |
| -------------- | -------------------------------- |
| `url`        | `https://yoursite.com/pricing` |
| `path`       | `/pricing`                     |
| `referrer`   | `https://google.com`           |
| `title`      | `Pricing — YourApp`           |
| `session_id` | `a1b2c3d4-...`                 |
| `user_agent` | `Mozilla/5.0 ...`              |
| `screen`     | `1920x1080`                    |
| `language`   | `en-US`                        |

## Verify It's Working

Open your EventPulse dashboard → **Live Feed** — you should see events appear within 5 seconds.
