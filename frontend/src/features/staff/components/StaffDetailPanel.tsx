import React from 'react';
import { ShieldCheck, Mail, CheckCircle2, UserCheck, ShieldAlert } from 'lucide-react';
import type { StaffMember, Role } from '../types';

interface StaffDetailPanelProps {
  selectedStaff: StaffMember | null;
  roles: Role[];
  isSaving: boolean;
  onRoleToggle: (roleId: number) => void;
  onSaveRoles: () => void;
}

export const StaffDetailPanel: React.FC<StaffDetailPanelProps> = ({
  selectedStaff,
  roles,
  isSaving,
  onRoleToggle,
  onSaveRoles
}) => {
  if (!selectedStaff) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 py-12">
        <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mb-4 text-slate-300">
          <UserCheck size={32} />
        </div>
        <p className="font-bold">スタッフを選択すると詳細と権限設定が表示されます</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* スタッフ基本ヘッダー */}
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-indigo-600 text-white flex items-center justify-center font-black text-2xl shadow-lg">
          {selectedStaff.name.charAt(0)}
        </div>
        <div>
          <h2 className="text-xl font-black text-slate-800 mb-1">{selectedStaff.name}</h2>
          <p className="text-sm text-slate-400 font-bold flex items-center gap-1">
            <span>コード:</span>
            <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 font-mono">
              {selectedStaff.staff_code}
            </span>
          </p>
        </div>
      </div>

      <hr className="border-slate-100" />

      {/* アカウント詳細情報 */}
      <div className="space-y-3">
        <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">アカウント情報</h3>
        <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100">
          <Mail size={16} className="text-slate-400" />
          <span className="text-sm font-bold text-slate-600">
            {selectedStaff.email || '未登録 / N/A'}
          </span>
        </div>
        <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100">
          {selectedStaff.is_active ? (
            <CheckCircle2 size={16} className="text-emerald-500" />
          ) : (
            <ShieldAlert size={16} className="text-slate-300" />
          )}
          <span className="text-sm font-bold text-slate-600">
            ステータス: {selectedStaff.is_active ? '稼働中' : '停止中'}
          </span>
        </div>
      </div>

      {/* ロール / 権限設定セクション */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
            <ShieldCheck size={14} className="text-indigo-500" />
            <span>権限ロール割り当て</span>
          </h3>
        </div>
        <div className="space-y-2">
          {roles.map((role) => {
            const isAssigned = selectedStaff.role_ids.includes(role.id);
            return (
              <label
                key={role.id}
                className={`
                  flex items-center justify-between p-4 rounded-2xl border-2 cursor-pointer transition-all
                  ${
                    isAssigned
                      ? 'border-indigo-500 bg-indigo-50/20 text-indigo-900 shadow-sm'
                      : 'border-slate-100 hover:border-slate-200 text-slate-500'
                  }
                `}
              >
                <div className="flex flex-col">
                  <span className="font-black text-sm">{role.name}</span>
                  <span className="text-[10px] opacity-75 font-bold uppercase tracking-wider">
                    スコープ: {role.scope}
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={isAssigned}
                  onChange={() => onRoleToggle(role.id)}
                  className="w-5 h-5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500/20 cursor-pointer"
                />
              </label>
            );
          })}
        </div>

        <button
          onClick={onSaveRoles}
          disabled={isSaving}
          className="w-full bg-gradient-to-tr from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-black py-4 px-6 rounded-2xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {isSaving ? (
            <>
              <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>保存中...</span>
            </>
          ) : (
            <span>権限を保存</span>
          )}
        </button>
      </div>
    </div>
  );
};
export default StaffDetailPanel;
