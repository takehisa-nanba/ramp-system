// frontend/src/components/LoginForm.tsx

import React, { useState, type FormEvent } from 'react';
// 🛠️ 修正: パスが正しくないため、拡張子 '.ts' を追加して解決を助ける
import { login } from '../services/authService.ts';

// App.tsx から AuthState 型をコピーして使用
type AuthState = {
  isLoggedIn: boolean;
  token: string | null;
  supporterName: string | null;
  role: string | null;
  error: string | null;
};

// =================================================================
// LoginForm コンポーネント
// =================================================================
const LoginForm: React.FC<{ onLoginSuccess: (authData: AuthState) => void }> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('sato@ramp.co.jp');
  const [password, setPassword] = useState('adminpassword');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const data = await login({ email, password });
      onLoginSuccess({
        isLoggedIn: true,
        token: null, 
        supporterName: data.full_name,
        role: "管理者",
        error: null,
      });
    } catch (err: any) {
      console.error(err);
      // エラーメッセージの形式が一致しない可能性があるため、汎用的なメッセージでエラーハンドリングを強化
      setError(err.message || 'ログインに失敗しました。認証サービスに問題がある可能性があります。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-900 font-sans p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="bg-indigo-600 p-8 text-center">
          <h2 className="text-3xl font-bold text-white tracking-wide">RAMP System</h2>
          <p className="text-indigo-100 mt-2 text-sm">職員向けセキュアログイン</p>
        </div>

        <div className="p-8">
          {error && (
            <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 rounded">
              <p className="text-sm text-red-700 font-bold">エラー</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">メールアドレス</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
                placeholder="name@company.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">パスワード</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '認証中...' : 'ログイン'}
            </button>
          </form>
          <div className="mt-8 pt-6 border-t border-gray-100 text-center">
            <p className="text-xs text-gray-400 font-mono">Test: sato@ramp.co.jp / adminpassword</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;