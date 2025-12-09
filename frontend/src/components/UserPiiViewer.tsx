// frontend/src/components/UserPiiViewer.tsx

import React, { useState } from 'react';
// 🛠️ 修正: パスの末尾に .ts を追加
import { fetchUserPii, type UserPiiResponse } from '../services/userService.ts'; 

// =================================================================
// UserPiiViewer コンポーネント
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

export default UserPiiViewer;