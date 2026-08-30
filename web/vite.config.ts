import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Relative asset paths so the same build works at a domain root (Vercel) and
  // under a repo subpath (GitHub Pages) without rebuilding for each.
  base: './',
  build: {
    outDir: 'dist',
  },
})
