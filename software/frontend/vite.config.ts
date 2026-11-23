import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend (FastAPI) runs on :8000; the dev server forwards /api to it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
