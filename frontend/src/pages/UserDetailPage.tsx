import React, { useEffect, useState } from 'react';
import { useParams, Routes, Route, NavLink } from 'react-router-dom';
import { User, Calendar, Activity, CheckCircle, AlertCircle } from 'lucide-react';
import { fetchUserPii, type UserPiiResponse } from '../services/userService';

const UserOverview: React.FC<{ userId: number }> = ({ userId }) => {
  const [user, setUser] = useState<UserPiiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const data = await fetchUserPii(userId);
        setUser(data);
      } catch (err) {
        console.error(err);
        setError('利用者情報の取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [userId]);

  if (loading) return (
    <div className="flex justify-center p-12">
      <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
    </div>
  );
  
  if (error || !user) return (
    <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error || 'データが見つかりません'}</div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in duration-500">
      {/* 基本情報カード */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
        <h2 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
          <User className="text-indigo-600 w-5 h-5" /> 基本情報
        </h2>
        <div className="space-y-4">
          <div>
            <div className="text-xs font-bold text-slate-400 mb-1">氏名</div>
            {user.pii.last_name === '********' ? (
              <div className="text-lg font-bold text-slate-800">********</div>
            ) : (
              <div className="text-lg font-bold text-slate-800">{user.pii.last_name} {user.pii.first_name} <span className="text-sm font-medium text-slate-500 ml-2">({user.pii.last_name_kana} {user.pii.first_name_kana})</span></div>
            )}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 mb-1">ステータス</div>
            <div className="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-bold">
              {user.status_name || '未設定'}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-bold text-slate-400 mb-1">生年月日</div>
              <div className="text-sm font-bold text-slate-700">{user.pii.birth_date ? new Date(user.pii.birth_date).toLocaleDateString() : '-'}</div>
            </div>
            <div>
              <div className="text-xs font-bold text-slate-400 mb-1">受給者証番号</div>
              <div className="text-sm font-bold text-slate-700">{user.pii.certificate_number || '-'}</div>
            </div>
          </div>
        </div>
      </div>

      {/* サービス利用状況カード */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
        <h2 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
          <Activity className="text-emerald-600 w-5 h-5" /> サービス利用状況
        </h2>
        <div className="space-y-4">
          <div>
            <div className="text-xs font-bold text-slate-400 mb-1 flex items-center gap-1"><Calendar className="w-3 h-3" /> 利用開始日</div>
            <div className="text-sm font-bold text-slate-700">{user.service_start_date ? new Date(user.service_start_date).toLocaleDateString() : '未設定'}</div>
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 mb-1">現在の個別支援計画</div>
            {user.support_plan ? (
              <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 p-3 rounded-xl text-sm font-bold">
                <CheckCircle className="w-4 h-4" /> 有効 ({user.support_plan.start_date ? new Date(user.support_plan.start_date).toLocaleDateString() : ''} 〜)
              </div>
            ) : (
              <div className="flex items-center gap-2 bg-amber-50 text-amber-700 p-3 rounded-xl text-sm font-bold">
                <AlertCircle className="w-4 h-4" /> 計画未作成・または無効
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

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
          <Route index element={<UserOverview userId={Number(id)} />} />
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
