import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Search, ChevronRight } from 'lucide-react';
import { fetchUserList, type UserListItem } from '../services/userService';

const UserListPage: React.FC = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadUsers = async () => {
      try {
        setLoading(true);
        const data = await fetchUserList();
        setUsers(data);
      } catch (err) {
        console.error(err);
        setError('利用者の取得に失敗しました');
      } finally {
        setLoading(false);
      }
    };
    loadUsers();
  }, []);

  return (
    <div className="p-6 md:p-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
            <Users className="text-indigo-600 w-8 h-8" />
            利用者一覧
          </h1>
          <p className="text-slate-500 mt-2 font-medium">登録されている利用者の一覧です。</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
          <input 
            type="text" 
            placeholder="名前で検索..." 
            className="pl-10 pr-4 py-2 border border-slate-200 rounded-full bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all w-64"
          />
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 text-rose-600 p-4 rounded-xl mb-6 font-bold">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center">
            <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
          </div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-bold">
            利用者が登録されていません
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-sm">
                <th className="py-4 px-6 font-bold">氏名</th>
                <th className="py-4 px-6 font-bold">ステータス</th>
                <th className="py-4 px-6 font-bold">受給者証</th>
                <th className="py-4 px-6 font-bold">サービス開始日</th>
                <th className="py-4 px-6 font-bold">計画終了日</th>
                <th className="py-4 px-6 font-bold text-center">詳細</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr 
                  key={user.id} 
                  onClick={() => navigate(`/users/${user.id}`)}
                  className="border-b border-slate-100 hover:bg-indigo-50/50 cursor-pointer transition-colors group"
                >
                  <td className="py-4 px-6 font-black text-slate-800">
                    {user.display_name}
                  </td>
                  <td className="py-4 px-6">
                    <span className="bg-indigo-100 text-indigo-700 px-3 py-1 rounded-full text-xs font-bold">
                      {user.status_name || '未設定'}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    {user.has_certificate_number ? (
                      <span className="text-emerald-600 font-bold text-sm flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-emerald-500"></div> 有り
                      </span>
                    ) : (
                      <span className="text-slate-400 font-medium text-sm flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-slate-300"></div> 無し
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-6 text-slate-600 font-medium">
                    {user.service_start_date ? new Date(user.service_start_date).toLocaleDateString() : '-'}
                  </td>
                  <td className="py-4 px-6 text-slate-600 font-medium">
                    {user.active_plan_end_date ? new Date(user.active_plan_end_date).toLocaleDateString() : '-'}
                  </td>
                  <td className="py-4 px-6 text-center">
                    <button className="text-slate-400 group-hover:text-indigo-600 transition-colors p-2 rounded-full group-hover:bg-indigo-100">
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default UserListPage;
