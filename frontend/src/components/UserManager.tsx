import React, { useState, useEffect } from 'react';
import { Search, Plus, Download, Upload, Eye, Loader2, Trash2, User } from 'lucide-react';
import { fetchUserList, fetchStatusMaster, decryptUserPii, type UserListItem, type StatusMaster } from '../services/userService';
import UserDetailModal from './common/UserDetailModal';
import { RegisterUserModal } from './common/RegisterUserModal';
import { StatusTransitionModal } from './common/StatusTransitionModal';

const TABS = [
  { id: 'active', label: '利用中', title: '利用者情報', subtitle: '対象者を選択してください' },
  { id: 'alumni', label: '利用終了', title: '利用修了者', subtitle: '過去に利用されていた方の一覧' },
  { id: 'inquiry', label: '問い合わせ', title: '問い合わせ管理', subtitle: '新規で問い合わせがあった方の一覧' },
];

export const UserManager: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'active' | 'alumni' | 'inquiry'>('active');
  const [statuses, setStatuses] = useState<StatusMaster[]>([]);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [searchTerm, setSearchTerm] = useState('');
  
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Modals
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [detailModalUserId, setDetailModalUserId] = useState<number | null>(null);
  const [transitionUser, setTransitionUser] = useState<any | null>(null);

  // Decrypted Certificates state
  const [decryptedCerts, setDecryptedCerts] = useState<Record<number, string>>({});
  const [decryptingIds, setDecryptingIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    const loadStatuses = async () => {
      try {
        const data = await fetchStatusMaster();
        setStatuses(data);
      } catch (err) {
        console.error("ステータスマスタの取得に失敗しました", err);
      }
    };
    loadStatuses();
  }, []);

  useEffect(() => {
    const loadUsers = async () => {
      if (statuses.length === 0) return;
      setLoading(true);
      
      try {
        let targetStatusNames: string[] = [];
        if (activeTab === 'active') targetStatusNames = ['利用中'];
        else if (activeTab === 'alumni') targetStatusNames = ['利用終了（退所）', '利用終了（定着支援中）', '利用終了（定着完了）'];
        else if (activeTab === 'inquiry') targetStatusNames = ['問い合わせ'];
        
        const targetIds = statuses.filter(s => targetStatusNames.includes(s.name)).map(s => s.id);
        
        const data = await fetchUserList(targetIds);
        setUsers(data);
        setDecryptedCerts({}); // リロード時は復号済みのものをリセット
      } catch (err: any) {
        console.error('利用者一覧の取得に失敗しました。', err);
      } finally {
        setLoading(false);
      }
    };
    
    loadUsers();
  }, [activeTab, statuses, refreshTrigger]);

  const handleDecryptCert = async (userId: number) => {
    if (decryptedCerts[userId]) return; // 既に復号済み
    
    setDecryptingIds(prev => new Set(prev).add(userId));
    try {
      const result = await decryptUserPii(userId, 'certificate_number');
      setDecryptedCerts(prev => ({ ...prev, [userId]: result.val }));
    } catch (err) {
      console.error(err);
      alert('受給者番号の取得に失敗しました。');
    } finally {
      setDecryptingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(userId);
        return newSet;
      });
    }
  };

  const filteredUsers = users.filter(u => 
    u.display_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    String(u.id).includes(searchTerm)
  );

  const currentTabInfo = TABS.find(t => t.id === activeTab)!;

  const handleDelete = async (userId: number, name: string) => {
    if (!window.confirm(`本当に「${name}」の情報を完全に削除しますか？\n※この操作は元に戻せません。`)) return;
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.msg || '削除に失敗しました');
      }
      setRefreshTrigger(prev => prev + 1);
    } catch (err: any) {
      alert(`削除エラー: ${err.message}`);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50/50 p-8 overflow-y-auto">
      
      {/* 画面ヘッダー */}
      <div className="max-w-6xl mx-auto w-full space-y-6">
        
        {/* タイトル行とアクションボタン */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-800">{currentTabInfo.title}</h1>
            <p className="text-xs font-bold text-slate-400 mt-1">{currentTabInfo.subtitle}</p>
          </div>
          <div className="flex items-center gap-3">
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-lg text-xs font-black shadow-sm hover:bg-slate-50 transition-all">
              <Upload size={14} />
              利用者情報のインポート
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-lg text-xs font-black shadow-sm hover:bg-slate-50 transition-all">
              <Download size={14} />
              書き出しする
            </button>
            <button 
              onClick={() => setIsRegisterModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg text-xs font-black shadow-sm shadow-indigo-200 transition-all"
            >
              <Plus size={14} />
              利用者を追加
            </button>
          </div>
        </div>

        {/* 検索ボックス */}
        <div className="bg-white border border-slate-200 rounded-xl p-2 shadow-sm flex items-center gap-3">
          <div className="pl-2">
            <Search size={16} className="text-slate-400" />
          </div>
          <input 
            type="text"
            placeholder="利用者名、受給者番号で検索"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="flex-1 bg-transparent border-none outline-none text-sm font-bold text-slate-700"
          />
        </div>

        {/* タブナビゲーション */}
        <div className="flex space-x-6 border-b border-slate-200">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 text-sm font-black transition-all border-b-2 ${
                activeTab === tab.id 
                  ? 'border-indigo-500 text-indigo-600' 
                  : 'border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* テーブル本体 */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <th className="py-4 px-6 text-xs font-black text-slate-600">氏名</th>
                {activeTab !== 'inquiry' && <th className="py-4 px-6 text-xs font-black text-slate-600">受給者番号</th>}
                {activeTab !== 'inquiry' && <th className="py-4 px-6 text-xs font-black text-slate-600">サービス提供開始日</th>}
                {activeTab !== 'inquiry' && <th className="py-4 px-6 text-xs font-black text-slate-600">個別支援計画の期限</th>}
                {activeTab === 'inquiry' && <th className="py-4 px-6 text-xs font-black text-slate-600">現在のステータス</th>}
                <th className="py-4 px-6"></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 className="animate-spin text-indigo-500 mx-auto mb-2" size={24} />
                    <p className="text-xs font-bold">読み込み中...</p>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <p className="text-xs font-bold">該当する利用者がいません</p>
                  </td>
                </tr>
              ) : (
                filteredUsers.map(user => (
                  <tr key={user.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center shrink-0">
                          <User size={14} />
                        </div>
                        <span className="text-sm font-black text-slate-700">{user.display_name}</span>
                      </div>
                    </td>
                    
                    {activeTab !== 'inquiry' && (
                      <td className="py-4 px-6">
                        {user.has_certificate_number ? (
                          <div className="flex items-center gap-2">
                            {decryptedCerts[user.id] ? (
                              <span className="text-sm font-bold text-slate-700 font-mono tracking-wider">{decryptedCerts[user.id]}</span>
                            ) : (
                              <>
                                <span className="text-sm font-bold text-slate-400 tracking-widest">*********</span>
                                <button 
                                  onClick={() => handleDecryptCert(user.id)}
                                  disabled={decryptingIds.has(user.id)}
                                  className="p-1.5 text-indigo-500 hover:bg-indigo-50 rounded-lg transition-colors"
                                >
                                  {decryptingIds.has(user.id) ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />}
                                </button>
                              </>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs font-bold text-slate-300">未登録</span>
                        )}
                      </td>
                    )}

                    {activeTab !== 'inquiry' && (
                      <td className="py-4 px-6">
                        <span className="text-sm font-bold text-slate-600">
                          {user.service_start_date ? user.service_start_date.replace(/-/g, '/') : '-'}
                        </span>
                      </td>
                    )}

                    {activeTab !== 'inquiry' && (
                      <td className="py-4 px-6">
                        <span className="text-sm font-bold text-slate-600">
                          {user.active_plan_end_date ? user.active_plan_end_date.replace(/-/g, '/') : '-'}
                        </span>
                      </td>
                    )}

                    {activeTab === 'inquiry' && (
                      <td className="py-4 px-6">
                        <span className="px-3 py-1 bg-orange-50 text-orange-600 rounded-full text-xs font-black border border-orange-100">
                          {user.status_name}
                        </span>
                      </td>
                    )}

                    <td className="py-4 px-6">
                      <div className="flex items-center justify-end gap-3">
                        {activeTab === 'inquiry' && (
                           <button
                             onClick={() => setTransitionUser(user)}
                             className="text-xs font-black text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition-colors"
                           >
                             利用開始にする
                           </button>
                        )}
                        <button 
                          onClick={() => handleDelete(user.id, user.display_name)}
                          className="flex items-center gap-1.5 text-xs font-black text-slate-400 hover:text-rose-500 transition-colors"
                        >
                          <Trash2 size={12} />
                          削除する
                        </button>
                        <button 
                          onClick={() => setDetailModalUserId(user.id)}
                          className="px-4 py-1.5 bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-lg text-xs font-black shadow-sm transition-all"
                        >
                          閲覧する
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* モーダル群 */}
      <UserDetailModal
        isOpen={detailModalUserId !== null}
        onClose={() => setDetailModalUserId(null)}
        userId={detailModalUserId}
        themeColor={activeTab === 'active' ? 'emerald' : activeTab === 'alumni' ? 'slate' : 'orange'}
        onDeleteSuccess={() => setRefreshTrigger(prev => prev + 1)}
        headerActions={(userData) => {
          if (activeTab === 'active') {
            return (
              <button
                onClick={() => setTransitionUser(userData)}
                className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 hover:text-rose-700 transition-all rounded-xl border border-rose-100 shadow-sm text-xs font-black"
              >
                利用終了にする
              </button>
            );
          } else if (activeTab === 'alumni' && userData.status_name === '利用終了（定着支援中）') {
             return (
              <button
                onClick={() => setTransitionUser(userData)}
                className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-600 hover:text-emerald-700 transition-all rounded-xl border border-emerald-100 shadow-sm text-xs font-black"
              >
                定着完了にする
              </button>
            );
          }
          return null;
        }}
      />

      <RegisterUserModal
        isOpen={isRegisterModalOpen}
        onClose={() => setIsRegisterModalOpen(false)}
        onRegisterSuccess={(newUserId) => {
          setRefreshTrigger(prev => prev + 1);
          setDetailModalUserId(newUserId);
        }}
      />

      {transitionUser && (() => {
        let title = '';
        let description = '';
        let targetNames: string[] = [];
        let requireStartDate = false;
        let requireEndDate = false;

        if (activeTab === 'inquiry') {
          title = '利用開始への移行';
          description = '問い合わせ段階から正式な利用へとステータスを移行します。サービス提供開始日を設定してください。';
          targetNames = ['利用中'];
          requireStartDate = true;
        } else if (activeTab === 'active') {
          title = '利用終了への移行';
          description = '利用中から利用終了へとステータスを移行します。利用終了日を設定してください。';
          targetNames = ['利用終了（退所）', '利用終了（定着支援中）', '利用終了（定着完了）'];
          requireEndDate = true;
        } else if (activeTab === 'alumni') {
          title = '定着完了への移行';
          description = '定着支援中から定着完了へとステータスを移行します。';
          targetNames = ['利用終了（定着完了）'];
        }

        const targetStatusList = statuses.filter(s => targetNames.includes(s.name));

        return (
          <StatusTransitionModal
            isOpen={true}
            onClose={() => setTransitionUser(null)}
            userId={transitionUser.id}
            userName={transitionUser.display_name}
            targetStatuses={targetStatusList}
            title={title}
            description={description}
            requireStartDate={requireStartDate}
            requireEndDate={requireEndDate}
            onSuccess={() => {
              setRefreshTrigger(prev => prev + 1);
            }}
          />
        );
      })()}
    </div>
  );
};

export default UserManager;
