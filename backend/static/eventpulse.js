/**
 * EventPulse Analytics SDK v1.0.0
 * Drop-in script for any website.
 *
 * Usage:
 *   <script src="https://eventpulse-analytics-backend.onrender.com/static/eventpulse.js"
 *           data-api-key="ep_live_YOUR_KEY"></script>
 *
 * Manual tracking:
 *   window.EventPulse.track("button_click", { button: "signup" });
 *   window.EventPulse.identify("user_123");
 */

(function (window) {
  "use strict";

  // -------------------------------------------------------------------------
  // Config
  // -------------------------------------------------------------------------

  var FLUSH_INTERVAL = 5000;   // ms — flush buffer every 5s
  var MAX_BUFFER     = 50;     // flush early if buffer hits this size
  var MAX_RETRIES    = 3;

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  var _apiKey    = null;
  var _baseUrl   = null;
  var _userId    = null;
  var _buffer    = [];
  var _timer     = null;
  var _retries   = 0;
  var _ready     = false;

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  function _uuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function _getSessionId() {
    try {
      var key = "_ep_sid";
      var sid = sessionStorage.getItem(key);
      if (!sid) { sid = _uuid(); sessionStorage.setItem(key, sid); }
      return sid;
    } catch (e) { return _uuid(); }
  }

  function _baseProperties() {
    return {
      url:        window.location.href,
      path:       window.location.pathname,
      referrer:   document.referrer || null,
      title:      document.title   || null,
      session_id: _getSessionId(),
      user_agent: navigator.userAgent,
      screen:     window.screen.width + "x" + window.screen.height,
      language:   navigator.language || null,
    };
  }

  // -------------------------------------------------------------------------
  // Buffer & Flush
  // -------------------------------------------------------------------------

  function _push(eventName, properties) {
    if (!_ready) return;

    _buffer.push({
      event_name:  eventName,
      user_id:     _userId || null,
      properties:  Object.assign(_baseProperties(), properties || {}),
      client_time: new Date().toISOString(),
    });

    if (_buffer.length >= MAX_BUFFER) _flush();
  }

  function _flush() {
    if (!_buffer.length) return;

    var events   = _buffer.slice();
    _buffer      = [];

    var payload  = JSON.stringify({ events: events });

    // Use sendBeacon when available (page unload safe)
    if (navigator.sendBeacon) {
      var blob = new Blob([payload], { type: "application/json" });
      var sent = navigator.sendBeacon(
        _baseUrl + "/api/v1/ingest/events/batch",
        blob
      );
      if (sent) { _retries = 0; return; }
    }

    // Fallback: fetch with retry
    fetch(_baseUrl + "/api/v1/ingest/events/batch", {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key":    _apiKey,
      },
      body:        payload,
      keepalive:   true,
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        _retries = 0;
      })
      .catch(function () {
        _retries++;
        if (_retries <= MAX_RETRIES) {
          // Re-queue failed events
          _buffer = events.concat(_buffer);
        }
      });
  }

  function _startTimer() {
    if (_timer) clearInterval(_timer);
    _timer = setInterval(_flush, FLUSH_INTERVAL);
  }

  // -------------------------------------------------------------------------
  // Auto-tracking
  // -------------------------------------------------------------------------

  function _trackPageView() {
    _push("page_view", {});
  }

  function _trackClicks() {
    document.addEventListener("click", function (e) {
      var el = e.target;
      // Walk up to find a meaningful element
      for (var i = 0; i < 5 && el; i++) {
        var tag = el.tagName ? el.tagName.toLowerCase() : "";
        if (tag === "a" || tag === "button" || el.getAttribute("data-track")) {
          _push("click", {
            element:  tag,
            text:     (el.innerText || "").trim().slice(0, 100),
            href:     el.href || null,
            id:       el.id   || null,
            class:    el.className || null,
          });
          return;
        }
        el = el.parentElement;
      }
    }, true);
  }

  function _trackPageLeave() {
    window.addEventListener("beforeunload", _flush);
    // visibilitychange covers mobile background
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") _flush();
    });
  }

  // SPA navigation support (React Router, Next.js, Vue Router)
  function _patchHistory() {
    function wrap(original) {
      return function () {
        var result = original.apply(this, arguments);
        _trackPageView();
        return result;
      };
    }
    history.pushState    = wrap(history.pushState);
    history.replaceState = wrap(history.replaceState);
    window.addEventListener("popstate", _trackPageView);
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  var EventPulse = {
    /**
     * Initialise the SDK manually (not needed if using data-api-key attribute).
     * @param {string} apiKey  Your ep_live_... key
     * @param {object} options { baseUrl, autoTrack }
     */
    init: function (apiKey, options) {
      options  = options || {};
      _apiKey  = apiKey;
      _baseUrl = (options.baseUrl || _detectBaseUrl()).replace(/\/$/, "");
      _ready   = true;

      if (options.autoTrack !== false) {
        _trackPageView();
        _trackClicks();
        _trackPageLeave();
        _patchHistory();
      }

      _startTimer();
      return this;
    },

    /**
     * Track a custom event.
     * @param {string} eventName
     * @param {object} properties
     */
    track: function (eventName, properties) {
      _push(eventName, properties);
      return this;
    },

    /**
     * Associate subsequent events with a user ID.
     * @param {string} userId
     */
    identify: function (userId) {
      _userId = userId;
      _push("identify", { identified_user_id: userId });
      return this;
    },

    /**
     * Manually flush the buffer (useful before logout).
     */
    flush: function () {
      _flush();
      return this;
    },
  };

  // -------------------------------------------------------------------------
  // Auto-init from <script data-api-key="...">
  // -------------------------------------------------------------------------

  function _detectBaseUrl() {
    // Try to find the script tag that loaded this file
    var scripts = document.querySelectorAll("script[src*='eventpulse']");
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].src;
      var match = src.match(/^(https?:\/\/[^/]+)/);
      if (match) return match[1];
    }
    return window.location.origin;
  }

  function _autoInit() {
    var scripts = document.querySelectorAll("script[data-api-key]");
    for (var i = 0; i < scripts.length; i++) {
      var key = scripts[i].getAttribute("data-api-key");
      if (key && key.indexOf("ep_") === 0) {
        EventPulse.init(key);
        return;
      }
    }
  }

  // Expose globally
  window.EventPulse = EventPulse;

  // Run auto-init after DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", _autoInit);
  } else {
    _autoInit();
  }

})(window);