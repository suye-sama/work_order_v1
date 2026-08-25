import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    // 代理配置：将 /api 开头的请求转发到 FastAPI 后端
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/agent': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
