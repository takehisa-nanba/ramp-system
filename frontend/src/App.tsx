// frontend/src/App.tsx

import React, { useState, FormEvent } from 'react';
import './index.css'; 

// ----------------------------------------------------------
// 🛠️ 修正: 作成済みのサービスを正しくインポート
// ----------------------------------------------------------
import { login } from './services/authService';
import { fetchUserPii, type UserPiiResponse } from './services/userService';

// 🛠️ 修正: プロキシを使うため、URLを相対パスに変更
const API_BASE_URL = '/api';

// 認証状態の型定義
type AuthState = {
  isLoggedIn: boolean;
  token: string | null;
  supporterName: string | null;
  role: string | null;
  error: string | null;
};

// =================================================================
// 1. ログインフォーム
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
      setError(err.message || 'ログインに失敗しました');
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

// =================================================================
// 2. PII取得テストコンポーネント
// =================================================================
const UserPiiViewer: React.FC = () => {
  const [userId, setUserId] = useState<number>(1);
  const [userData, setUserData] = useState<UserPiiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    setLoading(true);
    setError(null);
    setUserData(null);
    try {
      const data = await fetchUserPii(userId);
      setUserData(data);
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.msg || err.message || '情報の取得に失敗しました';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
      <div className="bg-gradient-to-r from-indigo-600 to-blue-600 px-6 py-4 flex justify-between items-center">
        <h3 className="text-lg font-bold text-white">PII セキュア閲覧</h3>
        <span className="text-xs font-bold bg-white/20 text-white px-3 py-1 rounded-full">VIEW_PII 権限</span>
      </div>
      
      <div className="p-6">
        <div className="flex flex-col sm:flex-row gap-4 mb-6 items-end">
          <div>
            <label className="block text-xs font-bold text-gray-500 mb-1">利用者ID</label>
            <input 
              type="number" 
              value={userId} 
              onChange={e => setUserId(Number(e.target.value))}
              className="w-full sm:w-24 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-center font-mono"
            />
          </div>
          <button 
            onClick={handleFetch}
            disabled={loading}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 shadow-sm"
          >
            {loading ? '復号中...' : '情報を取得'}
          </button>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 text-red-700 rounded-r">
            {error}
          </div>
        )}

        {userData && (
          <div className="bg-slate-50 rounded-xl border border-slate-200 overflow-hidden">
            <div className="bg-slate-100 px-6 py-3 border-b border-slate-200 flex justify-between items-center">
              <span className="text-xs font-bold text-slate-500">ID: {userData.id}</span>
              <span className="text-sm font-bold text-indigo-600 bg-white px-3 py-1 rounded-full shadow-sm">{userData.display_name}</span>
            </div>
            
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                <label className="block text-xs font-bold text-indigo-400 uppercase mb-1">氏名 (復号済)</label>
                <p className="text-xl font-bold text-slate-800">{userData.pii.last_name} {userData.pii.first_name}</p>
                <p className="text-sm text-slate-500">{userData.pii.last_name_kana} {userData.pii.first_name_kana}</p>
              </div>
              
              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
                <label className="block text-xs font-bold text-blue-400 uppercase mb-1">連絡先</label>
                <p className="text-sm text-slate-700 mb-1">📞 {userData.pii.phone_number}</p>
                <p className="text-sm text-slate-700">📧 {userData.pii.email}</p>
              </div>

              <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm md:col-span-2">
                <label className="block text-xs font-bold text-green-400 uppercase mb-1">住所 (復号済)</label>
                <p className="text-base text-slate-800">{userData.pii.address}</p>
              </div>
            </div>
            
            <div className="bg-slate-100 px-6 py-2 border-t border-slate-200 text-center">
              <p className="text-[10px] text-slate-400">🔒 この情報は暗号化されています</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// =================================================================
// 3. メイン App コンポーネント
// =================================================================
const App: React.FC = () => {
  const [auth, setAuth] = useState<AuthState>({
    isLoggedIn: false,
    token: null,
    supporterName: null,
    role: null,
    error: null,
  });

  const handleLogout = () => {
    setAuth({ isLoggedIn: false, token: null, supporterName: null, role: null, error: null });
  };

  if (!auth.isLoggedIn) {
    return <LoginForm onLoginSuccess={setAuth} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800">
      <nav className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold shadow-sm">R</div>
              <span className="font-bold text-xl text-slate-800">RAMP System</span>
            </div>
            <div className="flex items-center gap-6">
              <div className="hidden md:flex flex-col items-end">
                <span className="text-sm font-bold text-slate-700">{auth.supporterName}</span>
                <span className="text-xs text-indigo-600 font-medium bg-indigo-50 px-2 py-0.5 rounded">{auth.role}</span>
              </div>
              <button onClick={handleLogout} className="text-sm font-medium text-slate-500 hover:text-red-600 transition-colors">
                ログアウト
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">ダッシュボード</h1>
          <p className="text-slate-500 text-sm mt-1">本日の業務状況と各種データへのアクセス</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
            <UserPiiViewer />
            
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 opacity-50">
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-gray-400">日報管理</h3>
                <span className="text-xs bg-gray-100 text-gray-400 px-2 py-1 rounded">Coming Soon</span>
              </div>
              <div className="h-24 border-2 border-dashed border-gray-200 rounded-lg flex items-center justify-center text-gray-300 text-sm">
                次のスプリントで実装予定
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
              <h3 className="font-bold text-slate-800 mb-4 border-b border-gray-100 pb-2">クイックメニュー</h3>
              <div className="grid grid-cols-2 gap-3">
                <button className="p-3 bg-slate-50 hover:bg-slate-100 rounded-lg text-sm font-medium text-slate-600 transition text-center">
                  <span className="block text-2xl mb-1">👥</span>利用者一覧
                </button>
                <button className="p-3 bg-slate-50 hover:bg-slate-100 rounded-lg text-sm font-medium text-slate-600 transition text-center">
                  <span className="block text-2xl mb-1">📅</span>スケジュール
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;