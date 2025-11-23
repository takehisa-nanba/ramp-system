// frontend/src/App.tsx

import React, { useState } from 'react';
import './index.css'; 

// 責務分離されたコンポーネントをインポート
import LoginForm from './components/LoginForm';
import UserPiiViewer from './components/UserPiiViewer';
import PlanCreator from './components/PlanCreator';

// 認証状態の型定義 (各コンポーネントと共有)
type AuthState = {
  isLoggedIn: boolean;
  token: string | null;
  supporterName: string | null;
  role: string | null;
  error: string | null;
};

// =================================================================
// App コンポーネント (ルーター/レイアウトの役割のみ)
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
    // ログアウトAPI呼び出し（省略）
    setAuth({ isLoggedIn: false, token: null, supporterName: null, role: null, error: null });
  };

  // 1. ログイン画面の表示 (LoginFormに処理を委譲)
  if (!auth.isLoggedIn) {
    return <LoginForm onLoginSuccess={setAuth} />;
  }

  // 2. 認証後のダッシュボードレイアウト (コンポーネントを配置するだけ)
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800">
      <nav className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <span className="font-bold text-xl text-slate-800">RAMP System</span>
          <div className="flex items-center gap-4">
            <span className="text-sm font-bold text-slate-700">{auth.supporterName} ({auth.role})</span>
            <button onClick={handleLogout} className="text-sm font-medium text-slate-500 hover:text-red-600">ログアウト</button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* メイン機能エリア (左側 2/3) */}
        <div className="lg:col-span-2 space-y-8">
          {/* 計画作成ウィジェット */}
          <PlanCreator /> 
          {/* PII閲覧ウィジェット */}
          <UserPiiViewer />
          
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 opacity-50">
            <h3 className="font-bold text-gray-400">日報管理 (プレースホルダー)</h3>
          </div>
        </div>
        
        {/* サイドバーエリア (右側 1/3) */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 h-fit">
            <h3 className="font-bold text-slate-800 mb-4">クイックメニュー</h3>
            <p className="text-sm text-slate-500">App.tsxは、インポートと配置の責務に専念しています。</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;