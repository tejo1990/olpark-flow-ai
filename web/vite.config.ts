import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api/realtime-parking': {
        target: 'https://www.ksponco.or.kr',
        changeOrigin: true,
        rewrite: () => '/online/main/parkingorsApi.do?apiKey=PARKING21803504',
      },
    },
  },
});
