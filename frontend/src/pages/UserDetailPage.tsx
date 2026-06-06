import React from 'react';
import { useParams, Routes, Route, NavLink } from 'react-router-dom';

const UserDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">利用者詳細 (ID: {id})</h1>
      </div>

      {/* MVP Tabs */}
      <div className="flex gap-4 border-b border-slate-200 mb-6 pb-2">
        <NavLink to="." end className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>概要</NavLink>
        <NavLink to="support-plans" className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>計画</NavLink>
        <NavLink to="daily-logs" className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>日報</NavLink>
        <NavLink to="monitoring-reports" className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>モニタリング</NavLink>
        <NavLink to="case-conferences" className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>ケース会議</NavLink>
        <NavLink to="action-items" className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>管理確認事項</NavLink>
        <NavLink to="history" className={({ isActive }) => `pb-2 ${isActive ? 'font-bold text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-500'}`}>履歴</NavLink>
      </div>

      <div>
        <Routes>
          <Route index element={<div>利用者概要のプレースホルダー</div>} />
          <Route path="support-plans" element={<div>個別支援計画のプレースホルダー</div>} />
          <Route path="daily-logs" element={<div>日報のプレースホルダー</div>} />
          <Route path="monitoring-reports" element={<div>モニタリングのプレースホルダー</div>} />
          <Route path="case-conferences" element={<div>ケース会議のプレースホルダー</div>} />
          <Route path="action-items" element={<div>管理確認事項のプレースホルダー</div>} />
          <Route path="history" element={<div>履歴のプレースホルダー</div>} />
        </Routes>
      </div>
    </div>
  );
};

export default UserDetailPage;
