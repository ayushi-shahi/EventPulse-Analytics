import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Must be '/api/v1', not '/api'. The client-side route '/api-keys' also
      // starts with '/api', so the broader prefix made the dev server proxy a
      // page navigation to the backend — the API Keys page 500'd locally while
      // working fine in production, where no proxy exists.
      '/api/v1': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      }
    }
  }
})