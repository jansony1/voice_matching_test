import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

export default defineConfig({
  plugins: [
    vue(),
    nodePolyfills({
      protocolImports: true,
    }),
  ],
  resolve: {
    alias: {
      'buffer': 'buffer',
    }
  },
  define: {
    'process.env': {},
  },
  optimizeDeps: {
    include: ['buffer'],
  },
})
