import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const isProductionBuild = process.env.NODE_ENV === 'production';

export default defineConfig({
  base: isProductionBuild ? '/maste_data_analytics/' : '/',
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-axios': ['axios'],
          'vendor-charts': ['recharts'],
          'vendor-grid': ['ag-grid-community', 'ag-grid-react'],
        },
      },
    },
  },
});