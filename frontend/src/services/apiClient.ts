// frontend/src/services/apiClient.ts

import axios from 'axios'; // 値（axios.create）のみをインポート
import type { AxiosInstance, AxiosRequestConfig } from 'axios'; // 型（Type）のみをインポート
import Cookies from 'js-cookie';

// バックエンドのベースURL
// Viteの環境変数 VITE_API_BASE_URL を使用することを想定
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * 認証情報（Cookie）を伴う API リクエストクライアント
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // ★ 重要: CORSでCookieを送信するために必須の設定 ★
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * CSRF保護を伴うリクエストのインターセプター
 * POST, PUT, DELETE リクエストに X-CSRF-TOKEN ヘッダーを自動で付与します。
 */
// 🚨 修正: config の型注釈はそのまま使用できます
apiClient.interceptors.request.use((config: AxiosRequestConfig) => {
  // CSRF保護が有効な場合、Cookieからトークンを取得し、ヘッダーに設定
  if (config.method && ['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
    // Flask-JWT-Extended が設定するデフォルトの CSRF Cookie名
    const csrfToken = Cookies.get('csrf_access_token');
    
    if (csrfToken) {
      // Axiosのヘッダーに CSRF トークンを付与
      config.headers = {
        ...config.headers,
        'X-CSRF-TOKEN': csrfToken,
      };
    } else {
      // CSRFトークンが存在しない場合（ログインしていない状態など）
      // GETリクエスト以外は401を返すことが期待されるが、念のためログを出力
      console.warn('CSRF token is missing for a state-changing request.');
      // 実際には、この時点でリクエストを中断するロジックを検討しても良い
    }
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

export default apiClient;