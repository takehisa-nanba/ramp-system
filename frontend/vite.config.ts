import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // ★★★ 追加: 開発サーバーのプロキシ設定 ★★★
  server: {
    // Vite開発サーバーのポート（通常5173）
    port: 5173,
    // /api/ から始まるリクエストをバックエンドのFlaskサーバーに転送
    proxy: {
      '/api': {
        target: 'http://localhost:5000', // Flaskのデフォルトポート
        changeOrigin: true, // ホストヘッダーを変更
        rewrite: (path) => path.replace(/^\/api/, '/api'), // /api/auth/login のように転送
      },
    },
  },
  // ★★★ ここまで追加 ★★★
})