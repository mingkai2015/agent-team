import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/projects': 'http://localhost:8000',
      '/tasks': 'http://localhost:8000',
      '/requirements': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/phases': 'http://localhost:8000',
      '/workflow': 'http://localhost:8000',
      '/evaluation': 'http://localhost:8000',
      '/observability': 'http://localhost:8000',
      '/skills': 'http://localhost:8000',
      '/gitlab': 'http://localhost:8000',
    },
  },
})
