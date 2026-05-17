import React, { useState, useEffect } from 'react';
import { ShieldCheck, Mail, CheckCircle2, UserCheck, ShieldAlert, Edit, Save, X, Calendar, Clock, Briefcase } from 'lucide-react';
import type { StaffMember, Role } from '../types';

interface StaffDetailPanelProps {
  selectedStaff: StaffMember | null;
  roles: Role[];
  isSaving: boolean;
  onRoleToggle: (roleId: number) => void;
  onSaveRoles: () => void;
  onUpdateStaff: (data: any) => Promise<boolean>;
}

export const StaffDetailPanel: React.FC<StaffDetailPanelProps> = ({
  selectedStaff,
  roles,
  isSaving,
  onRoleToggle,
  onSaveRoles,
  onUpdateStaff
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    staff_code: '',
    email: '',
    employment_type: 'FULL_TIME',
    weekly_scheduled_minutes: 2400,
    hire_date: '',
    password: '',
    is_active: true
  });

  useEffect(() => {
    if (selectedStaff) {
      setFormData({
        last_name: selectedStaff.last_name || '',
        first_name: selectedStaff.first_name || '',
        last_name_kana: selectedStaff.last_name_kana || '',
        first_name_kana: selectedStaff.first_name_kana || '',
        staff_code: selectedStaff.staff_code || '',
        email: selectedStaff.email || '',
        employment_type: selectedStaff.employment_type || 'FULL_TIME',
        weekly_scheduled_minutes: selectedStaff.weekly_scheduled_minutes || 2400,
        hire_date: selectedStaff.hire_date || '',
        password: '',
        is_active: selectedStaff.is_active
      });
      setIsEditing(false);
    }
  }, [selectedStaff]);

  if (!selectedStaff) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 py-12">
        <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center mb-4 text-slate-300">
          <UserCheck size={32} />
        </div>
        <p className="font-bold text-sm">スタッフを選択すると詳細と権限設定が表示されます</p>
      </div>
    );
  }

  const handleSaveInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await onUpdateStaff(formData);
    if (success) {
      setIsEditing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. スタッフ基本ヘッダー */}
      <div className="flex items-center justify-between gap-4">
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

        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-indigo-200 text-indigo-600 hover:bg-indigo-50 text-xs font-black transition-all"
          >
            <Edit size={14} />
            <span>編集する</span>
          </button>
        )}
      </div>

      <hr className="border-slate-100" />

      {/* 2. メイン表示 / 編集モードの切り替え */}
      {isEditing ? (
        <form onSubmit={handleSaveInfo} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">氏（姓）</label>
              <input
                type="text"
                required
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              />
            </div>
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">名</label>
              <input
                type="text"
                required
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">氏かな（ふりがな）</label>
              <input
                type="text"
                required
                value={formData.last_name_kana}
                onChange={(e) => setFormData({ ...formData, last_name_kana: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              />
            </div>
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">名かな</label>
              <input
                type="text"
                required
                value={formData.first_name_kana}
                onChange={(e) => setFormData({ ...formData, first_name_kana: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">職員コード</label>
              <input
                type="text"
                required
                value={formData.staff_code}
                onChange={(e) => setFormData({ ...formData, staff_code: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-mono font-bold text-slate-800 transition-all"
              />
            </div>
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">入社日</label>
              <input
                type="date"
                required
                value={formData.hire_date}
                onChange={(e) => setFormData({ ...formData, hire_date: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-black text-slate-400 mb-1">メールアドレス</label>
            <input
              type="email"
              required
              inputMode="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">雇用形態</label>
              <select
                value={formData.employment_type}
                onChange={(e) => setFormData({ ...formData, employment_type: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              >
                <option value="FULL_TIME">常勤 (FULL_TIME)</option>
                <option value="SHORTENED_FT">時短常勤 (SHORTENED_FT)</option>
                <option value="PART_TIME">非常勤 (PART_TIME)</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-black text-slate-400 mb-1">週所定労働時間 (分)</label>
              <input
                type="number"
                required
                inputMode="numeric"
                min="0"
                value={formData.weekly_scheduled_minutes}
                onChange={(e) => setFormData({ ...formData, weekly_scheduled_minutes: intValue(e.target.value) })}
                className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-black text-slate-400 mb-1">パスワード (変更する場合のみ入力)</label>
            <input
              type="password"
              placeholder="新しいパスワード"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-xl px-3 py-2 text-sm font-bold text-slate-800 transition-all"
            />
          </div>

          <div className="flex items-center gap-2 py-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500/20 border-slate-300"
            />
            <label htmlFor="is_active" className="text-xs font-black text-slate-700 cursor-pointer">
              このスタッフアカウントを有効にする
            </label>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-black py-3 px-4 rounded-xl text-xs transition-all flex items-center justify-center gap-1.5"
            >
              <X size={14} />
              <span>キャンセル</span>
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 bg-gradient-to-tr from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-black py-3 px-4 rounded-xl text-xs shadow-md transition-all flex items-center justify-center gap-1.5"
            >
              <Save size={14} />
              <span>{isSaving ? '保存中...' : '情報を保存'}</span>
            </button>
          </div>
        </form>
      ) : (
        <div className="space-y-6">
          {/* 表示モードの基本情報 */}
          <div className="space-y-3">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">基本情報・雇用ステータス</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100">
                <Briefcase size={16} className="text-slate-400 flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-bold">雇用形態</span>
                  <span className="text-xs font-black text-slate-700">
                    {formData.employment_type === 'FULL_TIME' && '常勤'}
                    {formData.employment_type === 'SHORTENED_FT' && '時短常勤'}
                    {formData.employment_type === 'PART_TIME' && '非常勤'}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100">
                <Clock size={16} className="text-slate-400 flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-bold">週所定労働</span>
                  <span className="text-xs font-black text-slate-700">
                    {formData.weekly_scheduled_minutes}分 ({Math.round(formData.weekly_scheduled_minutes / 60)}時間)
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100 col-span-2">
                <Calendar size={16} className="text-slate-400 flex-shrink-0" />
                <div className="flex flex-col">
                  <span className="text-[10px] text-slate-400 font-bold">入社日</span>
                  <span className="text-xs font-black text-slate-700">
                    {formData.hire_date || '未設定'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest">アカウント情報</h3>
            <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100">
              <Mail size={16} className="text-slate-400 flex-shrink-0" />
              <span className="text-sm font-bold text-slate-600 break-all">
                {selectedStaff.email || '未登録 / N/A'}
              </span>
            </div>
            <div className="flex items-center gap-3 bg-slate-50 px-4 py-3 rounded-2xl border border-slate-100">
              {selectedStaff.is_active ? (
                <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />
              ) : (
                <ShieldAlert size={16} className="text-slate-300 flex-shrink-0" />
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
      )}
    </div>
  );
};

// ヘルパー: 文字列を安全に数値に変換する
const intValue = (val: string): number => {
  const parsed = parseInt(val, 10);
  return isNaN(parsed) ? 0 : parsed;
};

export default StaffDetailPanel;
