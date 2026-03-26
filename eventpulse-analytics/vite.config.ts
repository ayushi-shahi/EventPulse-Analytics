import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [dts({ insertTypesEntry: true })],
  esbuild: {
    jsx: 'automatic',
  },
  build: {
    lib: {
      entry: 'src/index.ts',
      name: 'EventPulseAnalytics',
      fileName: (format) => `eventpulse-analytics.${format}.js`,
    },
    rollupOptions: {
      external: ['react', 'react-dom', 'react/jsx-runtime', 'vue'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
          'react/jsx-runtime': 'ReactJSXRuntime',
          vue: 'Vue',
        },
      },
    },
  },
});