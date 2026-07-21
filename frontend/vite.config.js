import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/games': 'http://127.0.0.1:8000',
      '/chat': 'http://127.0.0.1:8000',
      '/ui': 'http://127.0.0.1:8000',
    },
  },
})
