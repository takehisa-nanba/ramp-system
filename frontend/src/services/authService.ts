import apiClient from './apiClient';
import { LoginRequest, Supporter, APIError } from '../types'; // 必要な型定義は後で作成

// ====================================================================
// 型定義 (仮): 実際のバックエンドモデルに合わせて調整が必要です
// ====================================================================
interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  msg: string;
  supporter_id: number;
  role_id: number;
  full_name: string;
}

// ====================================================================
// 認証サービス
// ====================================================================

/**
 * 職員ログイン処理
 * 成功すると、HTTP-Only Cookieにアクセストークンが設定されます。
 * @param data - ログイン情報 (email, password)
 */
export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  try {
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    
    // Cookieはブラウザが自動で処理するため、レスポンスボディからは削除されています
    // ここでユーザー情報を取得して返します
    return response.data; 

  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      // バックエンドからのエラーメッセージをキャッチ
      throw new Error(error.response.data.msg || 'ログインに失敗しました。');
    }
    throw new Error('ネットワークエラーまたはサーバーエラー');
  }
};

/**
 * ログアウト処理
 * サーバーにCookie削除を要求します。
 */
export const logout = async (): Promise<void> => {
  try {
    await apiClient.post('/auth/logout');
    // ログアウト後のクライアント側の状態管理は別途対応が必要です
  } catch (error) {
    // エラー処理（ここではログアウト失敗時でも強制的にクライアント側をログアウト状態にする方が安全）
    console.error('Logout API call failed:', error);
  }
};

/**
 * 認証が必要なテストAPIを呼び出す（CSRFヘッダーテストも兼ねる）
 */
export const fetchSalaries = async (): Promise<any> => {
    const response = await apiClient.get('/auth/salaries');
    return response.data;
};
