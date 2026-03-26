export interface EventPulseOptions {
  apiKey: string;
  endpoint: string;
  batchInterval?: number;
  autoTrack?: boolean;
}

export interface EventPayload {
  event_name: string;
  user_id?: string | null;
  properties?: Record<string, unknown>;
  timestamp?: string;
}

export class EventPulseClient {
  private apiKey: string;
  private endpoint: string;
  private batchInterval: number;
  private autoTrack: boolean;
  private queue: EventPayload[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private userId: string | null = null;
  private cleanupFns: (() => void)[] = [];

  constructor(options: EventPulseOptions) {
    this.apiKey = options.apiKey;
    this.endpoint = options.endpoint.replace(/\/$/, '');
    this.batchInterval = options.batchInterval ?? 5000;
    this.autoTrack = options.autoTrack ?? true;
    this.init();
  }

  private init() {
    this.timer = setInterval(() => this.flush(), this.batchInterval);

    if (this.autoTrack) {
      this.track('page_view', { url: window.location.href, referrer: document.referrer });

      const handleClick = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        this.track('click', {
          tag: target.tagName.toLowerCase(),
          id: target.id || null,
          text: target.innerText?.slice(0, 50) || null,
          url: window.location.href,
        });
      };
      document.addEventListener('click', handleClick);
      this.cleanupFns.push(() => document.removeEventListener('click', handleClick));
    }

    const handleUnload = () => this.flush(true);
    window.addEventListener('visibilitychange', handleUnload);
    this.cleanupFns.push(() => window.removeEventListener('visibilitychange', handleUnload));
  }

  track(eventName: string, properties?: Record<string, unknown>) {
    this.queue.push({
      event_name: eventName,
      user_id: this.userId,
      properties: properties ?? {},
      timestamp: new Date().toISOString(),
    });
  }

  identify(userId: string) {
    this.userId = userId;
    this.track('identify', { user_id: userId });
  }

  page(url?: string) {
    this.track('page_view', { url: url ?? window.location.href });
  }

  async flush(useBeacon = false) {
    if (this.queue.length === 0) return;
    const batch = [...this.queue];
    this.queue = [];
    const url = `${this.endpoint}/api/v1/ingest/events/batch`;
    const payload = JSON.stringify({ events: batch });

    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
      return;
    }

    try {
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': this.apiKey },
        body: payload,
      });
    } catch {
      this.queue = [...batch, ...this.queue];
    }
  }

  destroy() {
    if (this.timer) clearInterval(this.timer);
    this.cleanupFns.forEach(fn => fn());
    this.flush();
  }
}