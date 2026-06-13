// frontend/src/App.tsx

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css'; 

import LoginForm from './components/LoginForm';
import MainLayout from './components/layout/MainLayout';
import { useAuth } from './context/AuthContext';

// Pages
import DashboardPage from './pages/DashboardPage';
import UserListPage from './pages/UserListPage';
import UserDetailPage from './pages/UserDetailPage';
import ActionItemsPage from './pages/ActionItemsPage';
import SettingsPage from './pages/SettingsPage';
import TodayUsersPage from './pages/TodayUsersPage';
import { DailyScheduleActualPage } from './pages/DailyScheduleActualPage';


// =================================================================
// App コンポーネント (ルーター/レイアウトの役割のみ)
// =================================================================
const App: React.FC = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen bg-slate-900 text-white font-bold text-xl">読み込み中...</div>;
  }

  // 1. ログイン画面の表示 (LoginFormに処理を委譲)
  if (!isAuthenticated || !user) {
    return <LoginForm />;
  }

  // 2. 認証後のダッシュボードレイアウト (MainLayoutによるレスポンシブなサイドバー型)
  return (
    <BrowserRouter>
      <Routes>
        <Route 
          path="/" 
          element={
            <MainLayout 
              supporterName={user.fullName} 
              role={user.roleName} 
              onLogout={logout} 
            />
          }
        >
          {/* MainLayoutの <Outlet /> にレンダリングされる子ルート */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="today-users" element={<TodayUsersPage />} />
          <Route path="daily-schedules" element={<DailyScheduleActualPage />} />
          
          <Route path="users" element={<UserListPage />} />
          <Route path="users/:id/*" element={<UserDetailPage />} />
          
          <Route path="action-items" element={<ActionItemsPage />} />
          <Route path="settings" element={<SettingsPage />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;