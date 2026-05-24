import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Download, Upload, Eye, Loader2, Trash2 } from 'lucide-react';
import { fetchUserList, fetchStatusMaster, decryptUserPii, type UserListItem, type StatusMaster } from '../services/userService';
import { RegisterUserModal } from './common/RegisterUserModal';
import { StatusTransitionModal } from './common/StatusTransitionModal';
import { PremiumTable } from './common/PremiumTable';

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
  const navigate = useNavigate();

  // Modals
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
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
        <PremiumTable
          data={filteredUsers}
          isLoading={loading}
          keyExtractor={(u) => u.id}
          emptyMessage={
            activeTab === 'inquiry' ? '現在、新規の問い合わせはありません' : '該当する利用者がいません'
          }
          columns={[
            {
              header: '氏名',
              headerClassName: 'pl-8',
              className: 'pl-8',
              render: (user) => (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50/70 text-indigo-600 flex items-center justify-center font-black text-sm shrink-0 shadow-inner">
                    {user.display_name.charAt(0)}
                  </div>
                  <span className="text-sm font-black text-slate-700">{user.display_name}</span>
                </div>
              )
            },
            ...(activeTab !== 'inquiry' ? [{
              header: '受給者番号',
              render: (user: UserListItem) => (
                <div className="flex items-center gap-2">
                  {user.has_certificate_number ? (
                    decryptedCerts[user.id] ? (
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
                    )
                  ) : (
                    <span className="text-xs font-bold text-slate-300">未登録</span>
                  )}
                </div>
              )
            },
            {
              header: 'サービス提供開始日',
              render: (user: UserListItem) => (
                <span className="text-sm font-bold text-slate-600">
                  {user.service_start_date ? user.service_start_date.replace(/-/g, '/') : '-'}
                </span>
              )
            },
            {
              header: '個別支援計画の期限',
              render: (user: UserListItem) => (
                <span className="text-sm font-bold text-slate-600">
                  {user.active_plan_end_date ? user.active_plan_end_date.replace(/-/g, '/') : '-'}
                </span>
              )
            }] : []),
            ...(activeTab === 'inquiry' ? [{
              header: '現在のステータス',
              render: (user: UserListItem) => (
                <span className="px-3 py-1 bg-orange-50 text-orange-600 rounded-full text-xs font-black border border-orange-100">
                  {user.status_name}
                </span>
              )
            }] : []),
            {
              header: '操作',
              headerClassName: 'text-right pr-8',
              className: 'text-right pr-8',
              render: (user) => (
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
                    削除
                  </button>
                  <button 
                    onClick={() => navigate(`/users/${user.id}`)}
                    className="px-4 py-1.5 bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 rounded-lg text-xs font-black shadow-sm transition-all"
                  >
                    閲覧する
                  </button>
                </div>
              )
            }
          ]}
          renderMobileCard={(user) => (
            <div className="bg-white p-5 rounded-3xl border border-slate-100 shadow-sm space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-black text-sm shrink-0">
                    {user.display_name.charAt(0)}
                  </div>
                  <h3 className="font-black text-slate-800 text-base leading-tight">{user.display_name}</h3>
                </div>
                {activeTab === 'inquiry' ? (
                  <span className="text-[9px] font-black px-2 py-0.5 rounded-full border bg-orange-50 text-orange-600 border-orange-100">
                    {user.status_name}
                  </span>
                ) : (
                  <span className="text-[9px] font-black px-2 py-0.5 rounded-full border bg-indigo-50 text-indigo-600 border-indigo-100">
                    {activeTab === 'active' ? '利用中' : '利用終了'}
                  </span>
                )}
              </div>

              {activeTab !== 'inquiry' && (
                <div className="grid grid-cols-1 gap-2 pt-2 border-t border-slate-50 text-xs font-bold text-slate-500">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">受給者番号</span>
                    <div className="flex items-center gap-2">
                      {user.has_certificate_number ? (
                        decryptedCerts[user.id] ? (
                          <span className="text-sm font-bold text-slate-700 font-mono tracking-wider">{decryptedCerts[user.id]}</span>
                        ) : (
                          <>
                            <span className="text-sm font-bold text-slate-400 tracking-widest">*********</span>
                            <button 
                              onClick={() => handleDecryptCert(user.id)}
                              disabled={decryptingIds.has(user.id)}
                              className="p-1 text-indigo-500 hover:bg-indigo-50 rounded-lg transition-colors"
                            >
                              {decryptingIds.has(user.id) ? <Loader2 size={12} className="animate-spin" /> : <Eye size={12} />}
                            </button>
                          </>
                        )
                      ) : (
                        <span className="text-xs font-bold text-slate-300">未登録</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">個別支援計画期限</span>
                    <span className="text-slate-700">{user.active_plan_end_date ? user.active_plan_end_date.replace(/-/g, '/') : '-'}</span>
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-slate-50 flex items-center justify-between gap-2">
                <button 
                  onClick={() => handleDelete(user.id, user.display_name)}
                  className="flex items-center gap-1 text-xs font-black text-rose-400 hover:text-rose-500 transition-colors p-2"
                >
                  <Trash2 size={14} />
                </button>
                <div className="flex items-center gap-2">
                  {activeTab === 'inquiry' && (
                     <button
                       onClick={() => setTransitionUser(user)}
                       className="text-xs font-black text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-4 py-2 rounded-xl transition-colors"
                     >
                       利用開始にする
                     </button>
                  )}
                  <button 
                    onClick={() => navigate(`/users/${user.id}`)}
                    className="px-5 py-2.5 bg-slate-900 text-white hover:bg-slate-800 rounded-xl text-xs font-black shadow-md transition-all flex items-center justify-center min-w-[80px]"
                  >
                    閲覧
                  </button>
                </div>
              </div>
            </div>
          )}
        />
      </div>

      {/* モーダル群 */}
      <RegisterUserModal
        isOpen={isRegisterModalOpen}
        onClose={() => setIsRegisterModalOpen(false)}
        onRegisterSuccess={(newUserId) => {
          setRefreshTrigger(prev => prev + 1);
          navigate(`/users/${newUserId}`);
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
