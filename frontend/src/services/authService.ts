import apiClient from './apiClient';
import axios from 'axios';
import { LoginRequest, LoginResponse } from '../context/type'; // 共通型定義をインポート

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
    // Axiosを使用し、ログインAPIをコール
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    
    // 成功時、サーバーはHTTP-Only Cookieを設定し、レスポンスボディにユーザー情報を返します
    return response.data; 

  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      // バックエンドからのエラーメッセージ（例: 401 Invalid credentials）をキャッチ
      throw new Error(error.response.data.msg || 'ログインに失敗しました。メールアドレスまたはパスワードを確認してください。');
    }
    // その他のネットワークエラーなど
    throw new Error('ネットワークエラーまたはサーバーエラー');
  }
};

/**
 * ログアウト処理
 * サーバーにCookie削除を要求します。
 */
export const logout = async (): Promise<void> => {
  try {
    // ログアウトAPIをコール
    await apiClient.post('/auth/logout');
  } catch (error) {
    // エラー処理（ここではログアウト失敗時でも強制的にクライアント側をログアウト状態にする方が安全）
    console.error('ログアウトAPIコール中にエラー:', error);
    throw new Error('ログアウト処理中にエラーが発生しました。');
  }
};

/**
 * 認証が必要なテストAPIを呼び出す（CSRFヘッダーテストも兼ねる）
 */
export const fetchTestRoute = async (): Promise<any> => {
    try {
      const response = await apiClient.get('/auth/check');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        throw new Error(error.response.data.msg || '認証チェックに失敗しました。');
      }
      throw new Error('認証チェック通信エラー');
    }
};