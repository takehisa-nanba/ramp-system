// frontend/src/components/LoginForm.tsx

import React, { useState, type FormEvent } from 'react';
import { useAuth } from '../context/AuthContext';

// =================================================================
// LoginForm コンポーネント
// =================================================================

const LoginForm: React.FC = () => {
  const [userType, setUserType] = useState<'staff' | 'user'>('staff');
  const [loginId, setLoginId] = useState('admin@example.com');
  const [password, setPassword] = useState('password123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { login: authLogin } = useAuth();

  // クエリパラメータからセッション切れ（expired）フラグを解析
  const isExpired = new URLSearchParams(window.location.search).get('expired') === 'true';

  const handleUserTypeChange = (type: 'staff' | 'user') => {
    setUserType(type);
    if (type === 'staff') {
      setLoginId('admin@example.com');
    } else {
      setLoginId('USR001');
    }
    setPassword('password123');
    setError(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // AuthContext の login メソッドを呼び出す
      await authLogin({ login_id: loginId, password, user_type: userType });
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'ログインに失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-900 font-sans p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="bg-indigo-600 p-8 text-center">
          <h2 className="text-3xl font-bold text-white tracking-wide">RAMP System</h2>
          <p className="text-indigo-100 mt-2 text-sm">セキュアログイン</p>
        </div>

        <div className="p-8">
          {isExpired && !error && (
            <div className="mb-6 bg-amber-50 border-l-4 border-amber-500 p-4 rounded animate-pulse">
              <p className="text-sm text-amber-700 font-bold">セッション切れ</p>
              <p className="text-sm text-amber-600">セッションがタイムアウトしました。再度ログインしてください。</p>
            </div>
          )}

          {error && (
            <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 rounded">
              <p className="text-sm text-red-700 font-bold">エラー</p>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* ログイン種別タブ */}
          <div className="flex bg-slate-100 p-1 rounded-xl mb-6">
            <button
              type="button"
              onClick={() => handleUserTypeChange('staff')}
              className={`flex-1 py-2.5 text-sm font-bold rounded-lg transition-all duration-200 ${
                userType === 'staff'
                  ? 'bg-white text-indigo-600 shadow'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              職員ログイン
            </button>
            <button
              type="button"
              onClick={() => handleUserTypeChange('user')}
              className={`flex-1 py-2.5 text-sm font-bold rounded-lg transition-all duration-200 ${
                userType === 'user'
                  ? 'bg-white text-indigo-600 shadow'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              利用者ログイン
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">
                {userType === 'staff' ? '職員コード または メールアドレス' : '利用者コード または メールアドレス'}
              </label>
              <input
                type="text"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition"
                placeholder={userType === 'staff' ? 'admin-001 または name@example.com' : 'USR001 または name@example.com'}
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
            {userType === 'staff' ? (
              <>
                <p className="text-xs text-gray-400 font-mono">管理者: admin@example.com (または admin-001) / password123</p>
                <p className="text-xs text-gray-400 font-mono mt-1">一般職員: staff@example.com (または staff-001) / password123</p>
              </>
            ) : (
              <>
                <p className="text-xs text-gray-400 font-mono">佐藤健太: kenta.sato@example.com (または USR001) / password123</p>
                <p className="text-xs text-gray-400 font-mono mt-1">鈴木花子: hanako.suzuki@example.com (または USR002) / password123</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


export default LoginForm;