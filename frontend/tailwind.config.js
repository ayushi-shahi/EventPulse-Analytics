/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces, darkest to lightest. A analytics console reads better on a
        // dark ground: charts and status colours carry the signal, and the
        // chrome stays out of the way.
        ink: {
          950: '#08090d',   // page
          900: '#0d0f15',   // panel
          850: '#12141c',   // raised panel
          800: '#181b25',   // hover
          700: '#222633',   // border strong
          600: '#2d3242',   // border
        },
        // Single accent, used sparingly so it still means something.
        brand: {
          50:  '#eef2ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
        // Categorical series for charts — distinguishable at small sizes and
        // in the same lightness band so no series visually dominates.
        viz: {
          1: '#818cf8',
          2: '#22d3ee',
          3: '#4ade80',
          4: '#fbbf24',
          5: '#fb7185',
          6: '#c084fc',
          7: '#38bdf8',
          8: '#a3e635',
        },
        ok:   '#34d399',
        warn: '#fbbf24',
        bad:  '#fb7185',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      fontSize: {
        // Tabular figures for metrics so digits don't jitter while polling.
        'metric': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.02em', fontWeight: '600' }],
      },
      boxShadow: {
        panel: '0 1px 2px rgba(0,0,0,.4), 0 0 0 1px rgba(255,255,255,.04)',
        pop: '0 12px 32px -8px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.06)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn .18s ease-out',
        'slide-up': 'slideUp .22s cubic-bezier(.16,1,.3,1)',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: {
          from: { opacity: 0, transform: 'translateY(6px)' },
          to: { opacity: 1, transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
