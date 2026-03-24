import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      components: path.resolve(__dirname, 'src/components'),
      lib: path.resolve(__dirname, 'src/lib'),
      stores: path.resolve(__dirname, 'src/stores'),
      pages: path.resolve(__dirname, 'src/pages'),
      layouts: path.resolve(__dirname, 'src/layouts'),
      features: path.resolve(__dirname, 'src/features'),
      routes: path.resolve(__dirname, 'src/routes'),
      config: path.resolve(__dirname, 'src/config'),
      hooks: path.resolve(__dirname, 'src/hooks'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './vitest.setup.ts',
    globals: true
  }
});
