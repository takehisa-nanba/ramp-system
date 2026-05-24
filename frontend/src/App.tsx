// frontend/src/App.tsx

import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css'; 

// 責務分離されたコンポーネントをインポート
import LoginForm from './components/LoginForm';
import Dashboard from './components/Dashboard';
import Timecard from './components/Timecard';
import PlanCreator from './components/PlanCreator';
import UserManager from './components/UserManager';
import UserDetailPage from './components/UserDetailPage';
import MainLayout from './components/layout/MainLayout';
import DailyLogCreator from './components/DailyLogCreator';
import UserDashboard from './components/UserDashboard';
import LogSettings from './components/staff/LogSettings';
import StaffManagement from './components/StaffManagement';
import OfficeSettings from './components/OfficeSettings';
import { useAuth } from './context/AuthContext';


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
          <Route 
            index 
            element={
              user.roleName === 'STAFF' 
                ? <Dashboard supporterName={user.fullName} /> 
                : <UserDashboard userName={user.fullName} />
            } 
          />
          <Route path="timecard" element={<Timecard supporterName={user.fullName} />} />
          <Route path="users" element={<UserManager />} />
          <Route path="users/:id" element={<UserDetailPage />} />
          <Route path="plans" element={<PlanCreator />} />
          <Route path="daily-log" element={<DailyLogCreator />} />
          <Route path="settings/log" element={<LogSettings />} />
          <Route path="management/staff" element={<StaffManagement />} />
          <Route path="management/office" element={<OfficeSettings />} />


        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;