import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import Cookies from 'js-cookie';
import { AuthUser, LoginRequest, LoginResponse } from '../types';
// パスに拡張子 .ts を追加して解決を確実にします。
import { login as apiLogin, logout as apiLogout } from '../services/authService.ts'; // ★ 修正: .ts を追加 ★

// ====================================================================
// 1. Context の型定義
// ====================================================================

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

// 初期値（フックなしのダミー関数）
const defaultContextValue: AuthContextType = {
  user: null,
  isAuthenticated: false,
  login: () => Promise.reject(new Error("Auth Provider not initialized")),
  logout: () => Promise.reject(new Error("Auth Provider not initialized")),
  isLoading: false,
  error: null,
};

const AuthContext = createContext<AuthContextType>(defaultContextValue);

// ====================================================================
// 2. AuthProvider コンポーネント
// ====================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = user !== null;

  // ログイン処理
  const handleLogin = useCallback(async (data: LoginRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const response: LoginResponse = await apiLogin(data);
      
      // JWT claimsからの情報をUserオブジェクトとして構築 (ロール名が重要)
      const newUser: AuthUser = {
        id: response.supporter_id,
        fullName: response.full_name,
        roleId: response.role_id,
        // RoleNameはログイン時にAPIから取得されると仮定（JWT claimsから取得される想定）
        roleName: response.full_name.includes('管理者') ? '管理者' : '支援員' // 仮のロール決定ロジック
      };

      setUser(newUser);
      
    } catch (err: any) {
      console.error("Login failed:", err);
      setError(err.message || "ログインに失敗しました。");
      setUser(null);
      throw err; // コンポーネント側でエラー処理できるように再スロー
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ログアウト処理
  const handleLogout = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await apiLogout();
      setUser(null); // 状態をリセット
      // クライアント側の非HTTP-Only CSRFトークンCookieも削除（クリーンアップのため）
      Cookies.remove('csrf_access_token'); 
    } catch (err: any) {
      console.error("Logout failed:", err);
      // ログアウトAPIが失敗しても、クライアント状態は強制的にリセットする
      setUser(null); 
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 初期ロード時の処理
  useEffect(() => {
    // Note: HTTP-Only Cookieベースのため、セッションの自動復元はサーバーへの
    // /api/check_session のようなエンドポイントに依存します。
    // 現時点ではサーバー側でこのエンドポイントが未実装のため、初期状態はログアウトとして処理します。
    setIsLoading(false);
  }, []);

  const value = {
    user,
    isAuthenticated,
    login: handleLogin,
    logout: handleLogout,
    isLoading,
    error,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// ====================================================================
// 3. カスタムフック
// ====================================================================

/**
 * 認証コンテキストにアクセスするためのカスタムフック
 */
export const useAuth = () => {
  return useContext(AuthContext);
};
