// frontend/src/App.tsx

import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css'; 

// 責務分離されたコンポーネントをインポート
import LoginForm from './components/LoginForm';
import Dashboard from './components/Dashboard';
import Timecard from './components/Timecard';
import PlanCreator from './components/PlanCreator';
import UserPiiViewer from './components/UserPiiViewer';
import MainLayout from './components/layout/MainLayout';
import DailyLogCreator from './components/DailyLogCreator';

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

  // 2. 認証後のダッシュボードレイアウト (MainLayoutによるレスポンシブなサイドバー型)
  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/" 
          element={
            <MainLayout 
              supporterName={auth.supporterName} 
              role={auth.role} 
              onLogout={handleLogout} 
            />
          }
        >
          {/* MainLayoutの <Outlet /> にレンダリングされる子ルート */}
          <Route index element={<Dashboard supporterName={auth.supporterName} />} />
          <Route path="timecard" element={<Timecard supporterName={auth.supporterName} />} />
          <Route path="users" element={<UserPiiViewer />} />
          <Route path="plans" element={<PlanCreator />} />
          <Route path="daily-log" element={<DailyLogCreator />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;