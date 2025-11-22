import axios, { AxiosRequestConfig } from 'axios';
import Cookies from 'js-cookie';

// ★修正: 型エイリアスを使用して、AxiosInstanceを直接インポートしないことでモジュールエラーを回避
type AxiosInstanceType = axios.AxiosInstance;

// BASE_URL は Vite のプロキシ設定に合うように '/api' に統一
const BASE_URL = '/api'; 

/**
 * 認証情報（Cookie）を伴う API リクエストクライアント
 */
// ★修正: 型定義をAxiosInstanceTypeに変更
const apiClient: AxiosInstanceType = axios.create({
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
apiClient.interceptors.request.use((config: AxiosRequestConfig) => {
  // Flask-JWT-Extended が設定するデフォルトの CSRF Cookie名
  if (config.method && ['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
    const csrfToken = Cookies.get('csrf_access_token');
    
    if (csrfToken) {
      // Axiosのヘッダーに CSRF トークンを付与
      config.headers = {
        ...config.headers,
        'X-CSRF-TOKEN': csrfToken,
      };
    } else {
      // CSRFトークンが存在しない場合（ログインしていない状態など）
      console.warn('CSRF token is missing for a state-changing request.');
    }
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

export default apiClient;