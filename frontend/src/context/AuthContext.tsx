import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import Cookies from 'js-cookie';
// ★修正: 共通型定義から型をインポート
import type { AuthUser, LoginRequest, LoginResponse } from '../context/type'; 
// パスに拡張子 .ts を追加して解決を確実にします。
import { login as apiLogin, logout as apiLogout, checkSession } from '../services/authService'; 


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
      
      // ★修正ロジック: サーバーからのレスポンスを使用し、JWTからロール名を取得する
      // ★注: JWTはHTTP-Only Cookieに入っているため、クライアントでは直接デコードできません。
      // サーバーがレスポンスボディに full_name, role_name を返す前提で実装します。

      const newUser: AuthUser = {
        id: response.user_id,
        fullName: response.full_name,
        roleId: 0, // 互換性のため一旦0
        roleName: response.role_name
      };

      // localStorageの同期（既存コンポーネントとの互換性のため）
      localStorage.setItem('user_role', response.role_name);
      localStorage.setItem('user_role_scopes', JSON.stringify(response.role_scopes || []));
      localStorage.setItem('user_full_name', response.full_name);


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
      // JWTトークンがHTTP-Onlyの場合、ブラウザは自動で削除しますが、CSRFトークンは手動で削除
      Cookies.remove('csrf_access_token'); 
      localStorage.removeItem('user_role');
      localStorage.removeItem('user_role_scopes');
      localStorage.removeItem('user_full_name');
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
    const restoreSession = async () => {
      try {
        const response = await checkSession();
        const restoredUser: AuthUser = {
          id: response.user_id,
          fullName: response.full_name,
          roleId: 0,
          roleName: response.role_name
        };
        
        // localStorageの同期
        localStorage.setItem('user_role', response.role_name);
        localStorage.setItem('user_role_scopes', JSON.stringify(response.role_scopes || []));
        localStorage.setItem('user_full_name', response.full_name);
        
        setUser(restoredUser);
      } catch (err) {
        // セッションがない場合はそのままログアウト状態
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
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
