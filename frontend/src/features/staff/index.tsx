import React, { useState } from 'react';
import { Search, UserPlus, Sparkles, ShieldCheck } from 'lucide-react';
import { useStaff } from './hooks/useStaff';
import { StaffList } from './components/StaffList';
import { StaffDetailPanel } from './components/StaffDetailPanel';
import { RegisterStaffModal } from './components/RegisterStaffModal';

export const StaffManagement: React.FC = () => {
  const {
    staff,
    roles,
    isLoading,
    isSaving,
    selectedStaff,
    message,
    setSelectedStaff,
    handleRoleToggle,
    handleSaveRoles,
    handleRegister,
    handleUpdateStaff
  } = useStaff();

  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="max-w-[1600px] mx-auto p-4 sm:p-8 space-y-8 animate-fade-in">
      {/* 画面ヘッダー */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-100">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <div className="w-8 h-8 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
              <ShieldCheck size={18} />
            </div>
            <h1 className="text-2xl font-black text-slate-800 tracking-tight">職員権限・アカウント管理</h1>
          </div>
          <p className="text-xs text-slate-400 font-bold tracking-wide uppercase">
            事業所内のスタッフのアカウント作成、および業務に応じた権限ロールの割り当てを行います
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-black px-6 py-4 rounded-2xl shadow-lg hover:shadow-xl transition-all w-full sm:w-auto justify-center"
        >
          <UserPlus size={18} />
          <span>スタッフ新規登録</span>
        </button>
      </div>

      {/* ステータスメッセージ */}
      {message && (
        <div
          className={`
            px-6 py-4 rounded-2xl text-sm font-black flex items-center gap-2 border shadow-sm animate-bounce
            ${
              message.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }
          `}
        >
          <Sparkles size={16} className={message.type === 'success' ? 'text-emerald-500' : 'text-rose-500'} />
          <span>{message.text}</span>
        </div>
      )}

      {/* メイングリッドレイアウト */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* 左側：リストエリア */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center gap-3 bg-white px-5 py-4 rounded-[2rem] border border-slate-100 shadow-sm">
            <Search className="text-slate-400 shrink-0" size={20} />
            <input
              type="text"
              placeholder="氏名、または職員コードで検索..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-transparent border-0 outline-none w-full font-bold text-slate-700 placeholder-slate-300"
            />
          </div>

          <StaffList
            staff={staff}
            isLoading={isLoading}
            searchTerm={searchTerm}
            selectedStaff={selectedStaff}
            onSelectStaff={setSelectedStaff}
          />
        </div>

        {/* 右側：詳細・権限設定エリア */}
        <div className="bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-100 lg:sticky lg:top-8">
          <StaffDetailPanel
            selectedStaff={selectedStaff}
            roles={roles}
            isSaving={isSaving}
            onRoleToggle={handleRoleToggle}
            onSaveRoles={handleSaveRoles}
            onUpdateStaff={handleUpdateStaff}
          />
        </div>
      </div>

      {/* スタッフ新規登録モーダル */}
      <RegisterStaffModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        roles={roles}
        isSaving={isSaving}
        onRegister={handleRegister}
      />
    </div>
  );
};
export default StaffManagement;
