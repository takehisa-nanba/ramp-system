// frontend/src/App.tsx

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import './index.css'; 

import LoginForm from './components/LoginForm';
import MainLayout from './components/layout/MainLayout';
import UserLayout from './components/layout/UserLayout';
import { useAuth } from './context/AuthContext';

// Pages (Staff)
import DashboardPage from './pages/DashboardPage';
import UserListPage from './pages/UserListPage';
import UserDetailPage from './pages/UserDetailPage';
import ActionItemsPage from './pages/ActionItemsPage';
import SettingsPage from './pages/SettingsPage';
import { DailyScheduleActualPage } from './pages/DailyScheduleActualPage';
import AITestPage from './pages/AITestPage';
import StaffAttendancePage from './pages/StaffAttendancePage';
import SupportRecordsPage from './pages/SupportRecordsPage';
import JobRetentionStaffDashboardPage from './pages/JobRetentionStaffDashboardPage';
import JobRetentionMonthlyReportPage from './pages/JobRetentionMonthlyReportPage';

// Pages (User)
import { JobRetentionVoicePage } from './pages/JobRetentionVoicePage';
import { JobRetentionUserInfoPage } from './pages/JobRetentionUserInfoPage';

// =================================================================
// ルートガード (アクター分離・Fail Closed)
// =================================================================
const StaffRoute: React.FC<{ role?: string | null }> = ({ role }) => {
  if (role !== 'STAFF') {
    // 本人や他権限からのアクセスは遮断して本人画面へ
    return <Navigate to="/user/voice" replace />;
  }
  return <Outlet />;
};

const UserRoute: React.FC<{ role?: string | null }> = ({ role }) => {
  if (role !== 'USER') {
    // 支援員からのアクセスは遮断して支援員ダッシュボードへ
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
};

// =================================================================
// App コンポーネント
// =================================================================
const App: React.FC = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-900 text-white font-bold text-xl">
        読み込み中...
      </div>
    );
  }

  // 1. 未認証時はログイン画面
  if (!isAuthenticated || !user) {
    return <LoginForm />;
  }

  const isUser = user.roleName === 'USER';

  return (
    <BrowserRouter>
      <Routes>
        {/* ルートアクセス時のロール別振り分け */}
        <Route 
          path="/" 
          element={<Navigate to={isUser ? "/user/voice" : "/dashboard"} replace />} 
        />

        {/* ------------------------------------------------------------- */}
        {/* 2. 本人専用ルート (UserLayout + UserRouteガード) */}
        {/* ------------------------------------------------------------- */}
        <Route element={<UserRoute role={user.roleName} />}>
          <Route 
            path="/user" 
            element={
              <UserLayout 
                userName={user.fullName} 
                onLogout={logout} 
              />
            }
          >
            <Route index element={<Navigate to="/user/voice" replace />} />
            {/* できごとを残す */}
            <Route path="voice" element={<JobRetentionVoicePage defaultTab="create" />} />
            {/* 自分の過去の記録を見る */}
            <Route path="history" element={<JobRetentionVoicePage defaultTab="history" />} />
            {/* 自分の定着支援情報を見る */}
            <Route path="retention-info" element={<JobRetentionUserInfoPage />} />
          </Route>
        </Route>

        {/* ------------------------------------------------------------- */}
        {/* 3. 支援員専用ルート (MainLayout + StaffRouteガード) */}
        {/* ------------------------------------------------------------- */}
        <Route element={<StaffRoute role={user.roleName} />}>
          <Route 
            element={
              <MainLayout 
                supporterName={user.fullName} 
                role={user.roleName} 
                onLogout={logout} 
              />
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/daily-schedules" element={<DailyScheduleActualPage />} />
            
            <Route path="/users" element={<UserListPage />} />
            <Route path="/users/:id/*" element={<UserDetailPage />} />
            
            <Route path="/action-items" element={<ActionItemsPage />} />
            <Route path="/ai-test" element={<AITestPage />} />
            <Route path="/attendance" element={<StaffAttendancePage />} />
            <Route path="/records" element={<SupportRecordsPage />} />
            <Route path="/settings" element={<SettingsPage />} />

            {/* 就労定着支援ドメイン (支援員用) */}
            <Route path="/job-retention" element={<JobRetentionStaffDashboardPage />} />
            <Route path="/job-retention/:contractId/monthly-report" element={<JobRetentionMonthlyReportPage />} />
          </Route>
        </Route>

        {/* 4. Fallback (Fail Closed) */}
        <Route 
          path="*" 
          element={<Navigate to={isUser ? "/user/voice" : "/dashboard"} replace />} 
        />
      </Routes>
    </BrowserRouter>
  );
};

export default App;