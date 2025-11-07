import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  server: {
    // Add the specific host your tunnel uses:
    allowedHosts: [
      'hewlett-equality-southeast-opt.trycloudflare.com'
    ]
  },
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});



