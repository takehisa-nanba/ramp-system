// frontend/src/services/apiClient.ts

import axios from 'axios';
import type { AxiosInstance } from 'axios';
import Cookies from 'js-cookie';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  xsrfCookieName: 'csrf_access_token',
  xsrfHeaderName: 'X-CSRF-TOKEN',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 401 Unauthorized エラーのグローバルハンドリング
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response) {
      if (error.response.status === 401) {
        const currentPath = window.location.pathname;
        // 無限リダイレクトループを回避
        if (currentPath !== '/login') {
          // 安全な状態の破棄: 機密情報の全消去
          localStorage.clear();
          Cookies.remove('csrf_access_token');

          // タイムアウトフィードバック付きでログイン画面へリダイレクト
          window.location.href = '/login?expired=true';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;