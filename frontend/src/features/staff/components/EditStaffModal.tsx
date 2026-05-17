import React, { useState, useEffect } from 'react';
import { X, Sparkles, UserCheck, Type, Key, Mail, Calendar, Clock, ShieldCheck } from 'lucide-react';
import type { StaffMember, Role } from '../types';
import type { NewStaffData } from '../types';

interface EditStaffModalProps {
  isOpen: boolean;
  onClose: () => void;
  staff: StaffMember | null;
  roles: Role[];
  isSaving: boolean;
  onUpdate: (id: number, data: NewStaffData) => Promise<boolean>;
}

export const EditStaffModal: React.FC<EditStaffModalProps> = ({
  isOpen,
  onClose,
  staff,
  roles,
  isSaving,
  onUpdate
}) => {
  const [form, setForm] = useState({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    staff_code: '',
    email: '',
    employment_type: 'FULL_TIME',
    password: '',
    hire_date: '',
    weekly_scheduled_hours: '40',
    is_active: true,
    selected_role_ids: [] as number[]
  });

  const [validationError, setValidationError] = useState<string | null>(null);

  // スタッフが選択されたら、フォームデータを初期化・同期する
  useEffect(() => {
    if (staff) {
      setForm({
        last_name: staff.last_name || '',
        first_name: staff.first_name || '',
        last_name_kana: staff.last_name_kana || '',
        first_name_kana: staff.first_name_kana || '',
        staff_code: staff.staff_code || '',
        email: staff.email || '',
        employment_type: staff.employment_type || 'FULL_TIME',
        password: '', // パスワードはプレースホルダーのみ
        hire_date: staff.hire_date ? staff.hire_date.split('T')[0] : new Date().toISOString().split('T')[0],
        weekly_scheduled_hours: String((staff.weekly_scheduled_minutes || 2400) / 60),
        is_active: staff.is_active !== false,
        selected_role_ids: staff.role_ids || []
      });
      setValidationError(null);
    }
  }, [staff, isOpen]);

  if (!isOpen || !staff) return null;

  const handleRoleToggle = (roleId: number) => {
    setForm((prev) => ({
      ...prev,
      selected_role_ids: prev.selected_role_ids.includes(roleId)
        ? prev.selected_role_ids.filter((id) => id !== roleId)
        : [...prev.selected_role_ids, roleId]
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // バリデーション
    if (!form.last_name || !form.first_name) {
      setValidationError('氏名を入力してください。');
      return;
    }
    if (!form.last_name_kana || !form.first_name_kana) {
      setValidationError('フリガナを入力してください。');
      return;
    }
    const kanaRegex = /^[\u3040-\u309F\u30A1-\u30FC\s]+$/;
    if (!kanaRegex.test(form.last_name_kana) || !kanaRegex.test(form.first_name_kana)) {
      setValidationError('フリガナは全角ひらがな、または全角カタカナで入力してください。');
      return;
    }
    if (!form.staff_code) {
      setValidationError('職員コードを入力してください。');
      return;
    }
    if (!form.email || !form.email.includes('@')) {
      setValidationError('有効なメールアドレスを入力してください。');
      return;
    }
    const parsedHours = parseFloat(form.weekly_scheduled_hours);
    if (isNaN(parsedHours) || parsedHours <= 0 || parsedHours > 168) {
      setValidationError('週所定労働時間は1〜168時間の範囲で入力してください。');
      return;
    }

    const payload: NewStaffData = {
      last_name: form.last_name,
      first_name: form.first_name,
      last_name_kana: form.last_name_kana,
      first_name_kana: form.first_name_kana,
      staff_code: form.staff_code,
      email: form.email,
      employment_type: form.employment_type,
      password: form.password || undefined, // 入力があった場合のみ上書き更新
      hire_date: form.hire_date,
      weekly_scheduled_minutes: Math.round(parsedHours * 60),
      role_ids: form.selected_role_ids,
      is_active: form.is_active
    };

    const success = await onUpdate(staff.id, payload);
    if (success) {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-0 sm:p-4 animate-fade-in">
      <div className="bg-white w-full sm:max-w-2xl sm:rounded-[2.5rem] h-full sm:h-auto sm:max-h-[90vh] overflow-y-auto border border-slate-100 flex flex-col shadow-2xl">
        {/* モーダルヘッダー */}
        <div className="p-6 sm:p-8 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center">
              <UserCheck size={24} />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-800">職員情報の編集</h2>
              <p className="text-xs text-slate-400 font-bold">基本情報とシステムアクセス権限を編集します</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 rounded-xl bg-slate-50 hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* フォーム入力エリア */}
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6 flex-1">
          {validationError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-2xl text-sm font-bold flex items-center gap-2 animate-shake">
              <X size={16} className="text-rose-500 shrink-0" />
              <span>{validationError}</span>
            </div>
          )}

          {/* 氏名 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">姓</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Type size={16} className="text-slate-400 font-bold" />
                <input
                  type="text"
                  placeholder="例: 山田"
                  value={form.last_name}
                  onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">名</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Type size={16} className="text-slate-400 font-bold" />
                <input
                  type="text"
                  placeholder="例: 太郎"
                  value={form.first_name}
                  onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300"
                />
              </div>
            </div>
          </div>

          {/* フリガナ */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">セイ (フリガナ)</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Type size={16} className="text-slate-400 font-bold" />
                <input
                  type="text"
                  placeholder="例: ヤマダ"
                  value={form.last_name_kana}
                  onChange={(e) => setForm({ ...form, last_name_kana: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">メイ (フリガナ)</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Type size={16} className="text-slate-400 font-bold" />
                <input
                  type="text"
                  placeholder="例: タロウ"
                  value={form.first_name_kana}
                  onChange={(e) => setForm({ ...form, first_name_kana: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300"
                />
              </div>
            </div>
          </div>

          {/* 職員コード & メールアドレス */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">職員コード (必須)</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Key size={16} className="text-slate-400 font-bold" />
                <input
                  type="text"
                  placeholder="例: EMP-002"
                  value={form.staff_code}
                  onChange={(e) => setForm({ ...form, staff_code: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300 font-mono"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">メールアドレス</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Mail size={16} className="text-slate-400 font-bold" />
                <input
                  type="email"
                  placeholder="例: staff@example.com"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300"
                />
              </div>
            </div>
          </div>

          {/* 入社日 & 雇用区分 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">入社日</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Calendar size={16} className="text-slate-400 font-bold" />
                <input
                  type="date"
                  value={form.hire_date}
                  onChange={(e) => setForm({ ...form, hire_date: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold cursor-pointer"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">雇用区分</label>
              <select
                value={form.employment_type}
                onChange={(e) => setForm({ ...form, employment_type: e.target.value })}
                className="w-full bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3.5 text-slate-800 font-bold outline-none cursor-pointer"
              >
                <option value="FULL_TIME">常勤 (Full Time)</option>
                <option value="PART_TIME">非常勤 (Part Time)</option>
              </select>
            </div>
          </div>

          {/* パスワード & 週所定労働時間 (FTE分母計算用) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">新しいパスワード</label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <Key size={16} className="text-slate-400 font-bold" />
                <input
                  type="password"
                  placeholder="変更する場合のみ入力"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-400"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-1 font-bold">
                <Clock size={12} />
                <span>週所定労働時間 (常勤換算用)</span>
              </label>
              <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3">
                <input
                  type="number"
                  placeholder="例: 40"
                  step="0.5"
                  value={form.weekly_scheduled_hours}
                  onChange={(e) => setForm({ ...form, weekly_scheduled_hours: e.target.value })}
                  className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold text-right"
                />
                <span className="text-slate-400 font-bold text-sm">時間</span>
              </div>
            </div>
          </div>

          {/* 有効状態チェックボックス */}
          <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-2xl border border-slate-100">
            <input
              type="checkbox"
              id="is_active_checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="w-5 h-5 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 cursor-pointer"
            />
            <label htmlFor="is_active_checkbox" className="text-sm font-black text-slate-700 cursor-pointer select-none">
              このスタッフアカウントを有効にする（無効時はシステムにログインできません）
            </label>
          </div>

          {/* ロールの割り当てセクション */}
          <div className="space-y-3 pt-2">
            <label className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-1 font-bold">
              <ShieldCheck size={14} className="text-indigo-500 font-bold" />
              <span>付与する権限ロールの選択 (複数選択可)</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {roles.map((role) => {
                const isSelected = form.selected_role_ids.includes(role.id);
                return (
                  <button
                    type="button"
                    key={role.id}
                    onClick={() => handleRoleToggle(role.id)}
                    className={`
                      flex items-center justify-between p-4 rounded-2xl border-2 text-left transition-all
                      ${
                        isSelected
                          ? 'border-indigo-500 bg-indigo-50/20 text-indigo-900 font-black'
                          : 'border-slate-100 hover:border-slate-200 text-slate-500 font-bold'
                      }
                    `}
                  >
                    <div>
                      <div className="text-sm font-bold">{role.name}</div>
                      <div className="text-[9px] opacity-75 font-mono">Scope: {role.scope}</div>
                    </div>
                    <div
                      className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all
                        ${isSelected ? 'bg-indigo-600 border-indigo-600 text-white' : 'border-slate-300 bg-white'}
                      `}
                    >
                      {isSelected && <Sparkles size={10} className="fill-current" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* アクションボタン */}
          <div className="pt-4 flex gap-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-200 hover:bg-slate-50 text-slate-500 font-black py-4 px-6 rounded-2xl transition-all"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 bg-gradient-to-tr from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-black py-4 px-6 rounded-2xl shadow-lg hover:shadow-xl transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isSaving ? '保存中...' : '情報を保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
export default EditStaffModal;
