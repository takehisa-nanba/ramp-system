import React, { useState, useEffect } from 'react';
import { X, UserCheck, Type, Key, Mail, Calendar, Clock, ShieldCheck, Briefcase, Plus, Trash2, HelpCircle, Building2, Server } from 'lucide-react';
import type { StaffMember, Role, JobTitle, NewStaffData, JobAssignment } from '../types';

interface EditStaffModalProps {
  isOpen: boolean;
  onClose: () => void;
  staff: StaffMember | null;
  roles: Role[];
  jobTitles: JobTitle[];
  isSaving: boolean;
  onUpdate: (id: number, data: NewStaffData) => Promise<boolean>;
}

const DAYS_OF_WEEK = [
  { key: 'Monday', label: '月曜日' },
  { key: 'Tuesday', label: '火曜日' },
  { key: 'Wednesday', label: '水曜日' },
  { key: 'Thursday', label: '木曜日' },
  { key: 'Friday', label: '金曜日' },
  { key: 'Saturday', label: '土曜日' },
  { key: 'Sunday', label: '日曜日' }
];

export const EditStaffModal: React.FC<EditStaffModalProps> = ({
  isOpen,
  onClose,
  staff,
  roles,
  jobTitles,
  isSaving,
  onUpdate
}) => {
  // --- ログインユーザーの最高セキュリティ・ロールを判定し、特権昇格を防ぐ ---
  const getLoginUserMaxRole = (): 'SYSTEM' | 'CORPORATE' | 'JOB' | 'NONE' => {
    try {
      const scopesJson = localStorage.getItem('user_role_scopes');
      if (!scopesJson) return 'NONE';
      const scopes: string[] = JSON.parse(scopesJson);
      
      if (scopes.includes('SYSTEM')) return 'SYSTEM';
      if (scopes.includes('CORPORATE')) return 'CORPORATE';
      if (scopes.includes('JOB')) return 'JOB';
      return 'NONE';
    } catch {
      return 'NONE';
    }
  };

  const loginUserRole = getLoginUserMaxRole();

  // --- フォーム状態 ---
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
    retirement_date: '',
    weekly_scheduled_hours: '40',
    is_active: true,
    role_ids: [] as number[],
    
    // 暗号化個人情報 (PII)
    personal_phone: '',
    address: '',
    bank_account_info: '',
    
    // 実務職務設定用
    main_job_title_id: 0,
    main_is_deemed_assignment: false,
    main_deemed_expiry_date: '',
    is_multiple_jobs: false,
    allow_overlap_calculation: false,
    job_assignments: [] as { job_title_id: number; hours: string; is_deemed_assignment?: boolean; deemed_expiry_date?: string }[],

    // ★ 曜日別契約シフト設定用
    is_shift_pattern_enabled: false,
    shift_patterns: [] as { day_of_week: string; start_time: string; end_time: string; break_minutes: number; is_active: boolean }[]
  });

  const [validationError, setValidationError] = useState<string | null>(null);
  const [isPiiOpen, setIsPiiOpen] = useState(false);

  // カタカナ自動変換
  const toKatakana = (val: string) => {
    return val.replace(/[\u3041-\u3096]/g, (match) => {
      return String.fromCharCode(match.charCodeAt(0) + 0x60);
    });
  };

  // --- 3つのセキュリティレイヤー（システム・法人・事業所）それぞれのセレクトボックス変更ハンドラー ---
  const handleLayerRoleChange = (layer: 'SYSTEM' | 'CORPORATE' | 'JOB_LAYER', newRoleId: number) => {
    setForm(prev => {
      const sysRole = roles.find(r => r.scope === 'SYSTEM');
      const corpRole = roles.find(r => r.scope === 'CORPORATE');
      const jobRole = roles.find(r => r.scope === 'JOB');
      const staffRole = roles.find(r => r.scope === 'STAFF');

      let updated = [...prev.role_ids];

      if (layer === 'SYSTEM') {
        if (sysRole) updated = updated.filter(id => id !== sysRole.id);
        if (newRoleId > 0) updated.push(newRoleId);
      } else if (layer === 'CORPORATE') {
        if (corpRole) updated = updated.filter(id => id !== corpRole.id);
        if (newRoleId > 0) updated.push(newRoleId);
      } else if (layer === 'JOB_LAYER') {
        if (jobRole) updated = updated.filter(id => id !== jobRole.id);
        if (staffRole) updated = updated.filter(id => id !== staffRole.id);
        if (newRoleId > 0) updated.push(newRoleId);
      }

      return { ...prev, role_ids: updated };
    });
  };

  // --- スタッフデータ読み込み＆フォームの同期 ---
  useEffect(() => {
    if (staff && isOpen) {
      const weeklyHours = (staff.weekly_scheduled_minutes || 2400) / 60;
      
      // セキュリティロール (role_ids) の初期値マッピング (空なら一般支援員をフォールバック)
      const staffRole = roles.find(r => r.scope === 'STAFF');
      const initialRoleIds = staff.role_ids && staff.role_ids.length > 0 
        ? staff.role_ids 
        : (staffRole ? [staffRole.id] : []);
      
      // 実務職務 (job_assignments) の解析
      const assignments = staff.job_assignments || [];
      const isMulti = assignments.length > 1 || (assignments.length === 1 && (assignments[0].assigned_minutes / 60) !== weeklyHours);
      
      const mainJobId = assignments.length > 0 ? assignments[0].job_title_id : (jobTitles[0]?.id || 0);
      
      const mappedAssignments = assignments.map(a => ({
        job_title_id: a.job_title_id,
        hours: String(a.assigned_minutes / 60),
        is_deemed_assignment: !!a.is_deemed_assignment,
        deemed_expiry_date: a.deemed_expiry_date ? a.deemed_expiry_date.split('T')[0] : ''
      }));

      const singleAssignment = assignments[0];
      const mainIsDeemed = singleAssignment ? !!singleAssignment.is_deemed_assignment : false;
      const mainDeemedExpiry = (singleAssignment && singleAssignment.deemed_expiry_date) 
        ? singleAssignment.deemed_expiry_date.split('T')[0] 
        : '';

      // 曜日別シフトの解析
      const apiPatterns = staff.shift_patterns || [];
      const isShiftEnabled = apiPatterns.length > 0;
      const mappedPatterns = DAYS_OF_WEEK.map(d => {
        const found = apiPatterns.find(p => p.day_of_week === d.key);
        return {
          day_of_week: d.key,
          start_time: found?.start_time || '09:00',
          end_time: found?.end_time || '18:00',
          break_minutes: found ? found.break_minutes : 60,
          is_active: !!found
        };
      });

      setForm({
        last_name: staff.last_name || '',
        first_name: staff.first_name || '',
        last_name_kana: staff.last_name_kana || '',
        first_name_kana: staff.first_name_kana || '',
        staff_code: staff.staff_code || '',
        email: staff.email || '',
        employment_type: staff.employment_type || 'FULL_TIME',
        password: '',
        hire_date: staff.hire_date ? staff.hire_date.split('T')[0] : new Date().toISOString().split('T')[0],
        retirement_date: staff.retirement_date ? staff.retirement_date.split('T')[0] : '',
        weekly_scheduled_hours: String(weeklyHours),
        is_active: staff.is_active !== false,
        role_ids: initialRoleIds,
        
        personal_phone: staff.personal_phone || '',
        address: staff.address || '',
        bank_account_info: staff.bank_account_info || '',
        
        main_job_title_id: mainJobId,
        main_is_deemed_assignment: mainIsDeemed,
        main_deemed_expiry_date: mainDeemedExpiry,
        is_multiple_jobs: isMulti,
        allow_overlap_calculation: staff.allow_overlap_calculation === true,
        job_assignments: mappedAssignments.length > 0 ? mappedAssignments : [{ job_title_id: mainJobId, hours: String(weeklyHours), is_deemed_assignment: false, deemed_expiry_date: '' }],

        is_shift_pattern_enabled: isShiftEnabled,
        shift_patterns: mappedPatterns
      });
      setValidationError(null);
    }
  }, [staff, isOpen, jobTitles]);

  if (!isOpen || !staff) return null;

  // --- リアルタイム兼務時間合計の算出 ＆ バリデーションチェック ---
  const contractHours = parseFloat(form.weekly_scheduled_hours) || 0;
  const assignedHoursSum = form.is_multiple_jobs
    ? form.job_assignments.reduce((sum, item) => sum + (parseFloat(item.hours) || 0), 0)
    : contractHours;

  const isHoursMismatch = !form.allow_overlap_calculation && form.is_multiple_jobs && assignedHoursSum > contractHours;

  // 曜日ごとの実働時間（時間換算）を計算
  const calculateShiftWorkingHours = (pattern: typeof form.shift_patterns[0]) => {
    if (!pattern.is_active || !pattern.start_time || !pattern.end_time) return 0;
    const [sh, sm] = pattern.start_time.split(':').map(Number);
    const [eh, em] = pattern.end_time.split(':').map(Number);
    
    const startMinutes = sh * 60 + sm;
    const endMinutes = eh * 60 + em;
    
    if (endMinutes <= startMinutes) return 0;
    
    const workingMinutes = (endMinutes - startMinutes) - pattern.break_minutes;
    return Math.max(0, workingMinutes / 60);
  };

  const totalShiftWorkingHours = form.is_shift_pattern_enabled
    ? form.shift_patterns.reduce((sum, p) => sum + calculateShiftWorkingHours(p), 0)
    : 0;

  const isShiftHoursMismatch = form.is_shift_pattern_enabled && Math.abs(totalShiftWorkingHours - contractHours) > 0.01;

  // --- ハンドラ ---
  const handleAddJobAssignment = () => {
    const unusedTitle = jobTitles.find(t => !form.job_assignments.some(a => a.job_title_id === t.id));
    const nextJobId = unusedTitle ? unusedTitle.id : (jobTitles[0]?.id || 0);
    
    setForm(prev => ({
      ...prev,
      job_assignments: [...prev.job_assignments, { job_title_id: nextJobId, hours: '0' }]
    }));
  };

  const handleRemoveJobAssignment = (index: number) => {
    setForm(prev => ({
      ...prev,
      job_assignments: prev.job_assignments.filter((_, i) => i !== index)
    }));
  };

  const handleJobAssignmentChange = (index: number, field: string, value: any) => {
    setForm(prev => {
      const updated = [...prev.job_assignments];
      updated[index] = {
        ...updated[index],
        [field]: field === 'job_title_id' ? parseInt(value) : value
      };
      return { ...prev, job_assignments: updated };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // 基本情報バリデーション
    if (!form.last_name || !form.first_name) {
      setValidationError('氏名を入力してください。');
      return;
    }
    if (!form.last_name_kana || !form.first_name_kana) {
      setValidationError('フリガナを入力してください。');
      return;
    }

    // 送信時にひらがなをカタカナへ自動変換
    const lastNameKanaConverted = toKatakana(form.last_name_kana.trim());
    const firstNameKanaConverted = toKatakana(form.first_name_kana.trim());

    // カタカナとスペース、長音符以外が混ざっていないかチェック
    const kanaRegex = /^[ァ-ヴー\s　]+$/;
    if (!kanaRegex.test(lastNameKanaConverted) || !kanaRegex.test(firstNameKanaConverted)) {
      setValidationError('フリガナは全角カタカナ、または全角ひらがなで入力してください。カタカナ以外の無効な文字（英数字や漢字など）が含まれています。');
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
    if (contractHours <= 0 || contractHours > 168) {
      setValidationError('週所定労働時間は1〜168時間の範囲で入力してください。');
      return;
    }

    // 兼務時間バリデーション（特例OFF時、週労働時間を超えてはいけない）
    if (isHoursMismatch) {
      setValidationError(`各職務の割り当て合計（${assignedHoursSum.toFixed(1)}時間）が、週所定労働時間（${contractHours.toFixed(1)}時間）を超えています。時間を調整するか、特例フラグをONにしてください。`);
      return;
    }

    // API Payload 構築

    // 実務職務割り当て (job_assignments) の生成
    let finalAssignments: JobAssignment[] = [];
    if (form.is_multiple_jobs) {
      finalAssignments = form.job_assignments.map(a => ({
        job_title_id: a.job_title_id,
        assigned_minutes: Math.round((parseFloat(a.hours) || 0) * 60),
        is_deemed_assignment: !!a.is_deemed_assignment,
        deemed_expiry_date: a.is_deemed_assignment ? (a.deemed_expiry_date || null) : null
      }));
    } else {
      // 単一職務の場合は、契約時間の100%を自動割り当て
      finalAssignments = [{
        job_title_id: form.main_job_title_id > 0 ? form.main_job_title_id : (jobTitles[0]?.id || 1),
        assigned_minutes: Math.round(contractHours * 60),
        is_deemed_assignment: !!form.main_is_deemed_assignment,
        deemed_expiry_date: form.main_is_deemed_assignment ? (form.main_deemed_expiry_date || null) : null
      }];
    }

    // 曜日別シフトの payload 生成
    let finalShiftPatterns: any[] = [];
    if (form.is_shift_pattern_enabled) {
      finalShiftPatterns = form.shift_patterns
        .filter(p => p.is_active)
        .map(p => ({
          day_of_week: p.day_of_week,
          start_time: p.start_time,
          end_time: p.end_time,
          break_minutes: p.break_minutes
        }));
    }

    const payload: NewStaffData = {
      last_name: form.last_name,
      first_name: form.first_name,
      last_name_kana: lastNameKanaConverted,
      first_name_kana: firstNameKanaConverted,
      staff_code: form.staff_code,
      email: form.email,
      employment_type: form.employment_type,
      password: form.password || undefined,
      hire_date: form.hire_date,
      retirement_date: form.retirement_date || null,
      weekly_scheduled_minutes: Math.round(contractHours * 60),
      role_ids: form.role_ids,
      allow_overlap_calculation: form.allow_overlap_calculation,
      is_active: form.is_active,
      job_assignments: finalAssignments,
      shift_patterns: finalShiftPatterns,
      personal_phone: form.personal_phone || undefined,
      address: form.address || undefined,
      bank_account_info: form.bank_account_info || undefined
    };

    const success = await onUpdate(staff.id, payload);
    if (success) {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-0 sm:p-4 animate-fade-in overflow-y-auto">
      <div className="bg-white w-full sm:max-w-2xl sm:rounded-[2.5rem] my-auto border border-slate-100 flex flex-col shadow-2xl overflow-hidden animate-slide-up">
        {/* モーダルヘッダー */}
        <div className="p-6 sm:p-8 border-b border-slate-100 flex items-center justify-between bg-white sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-tr from-indigo-50 to-indigo-100/50 text-indigo-600 rounded-2xl flex items-center justify-center">
              <UserCheck size={24} />
            </div>
            <div>
              <h2 className="text-xl font-black text-slate-800">職員情報の編集</h2>
              <p className="text-xs text-slate-400 font-bold">基本情報とシステムアクセス権限・職務を管理します</p>
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
        <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {validationError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-2xl text-sm font-bold flex items-center gap-2 animate-shake">
              <X size={16} className="text-rose-500 shrink-0" />
              <span>{validationError}</span>
            </div>
          )}

          {/* セクションA: 基本情報 */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-1 border-b border-slate-50">
              <Type size={16} className="text-indigo-500 font-bold" />
              <h3 className="text-sm font-black text-slate-800">1. 基本情報</h3>
            </div>

            {/* 氏名 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">姓</label>
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 cursor-pointer">
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
                  className="w-full bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 text-slate-800 font-bold outline-none cursor-pointer focus:border-indigo-500 focus:bg-white border-2"
                >
                  <option value="FULL_TIME">常勤 (Full Time)</option>
                  <option value="PART_TIME">非常勤 (Part Time)</option>
                </select>
              </div>
            </div>

            {/* 退職日 ＆ アカウント状態 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold flex items-center justify-between">
                  <span>退職日 (設定時のみ常勤換算打切り適用)</span>
                  {form.retirement_date && (
                    <button 
                      type="button" 
                      onClick={() => setForm({ ...form, retirement_date: '' })} 
                      className="text-[10px] text-rose-500 hover:text-rose-600 transition-colors font-bold normal-case"
                    >
                      クリア
                    </button>
                  )}
                </label>
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 cursor-pointer">
                  <Calendar size={16} className="text-slate-400 font-bold" />
                  <input
                    type="date"
                    value={form.retirement_date}
                    onChange={(e) => setForm({ ...form, retirement_date: e.target.value })}
                    className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold cursor-pointer"
                  />
                </div>
              </div>
              <div className="space-y-2 flex flex-col justify-end pb-3">
                <label className="flex items-center gap-3 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <span className="text-xs font-bold text-slate-700">アカウントを有効にする</span>
                    <p className="text-[9px] text-slate-400 font-bold mt-0.5">※チェックを外すと一覧・集計から一時非表示になります</p>
                  </div>
                </label>
              </div>
            </div>

            {/* パスワード & 週所定労働時間 (FTE分母計算用) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">新しいパスワード</label>
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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
                  <span>週所定労働時間 (契約時間)</span>
                </label>
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 focus-within:border-indigo-500 focus-within:bg-white transition-all">
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

            {/* 🔒 暗号化個人情報 (PII) アコーディオン */}
            <div className="mt-4 border border-indigo-100 rounded-2xl bg-indigo-50/5 overflow-hidden transition-all duration-300">
              <button
                type="button"
                onClick={() => setIsPiiOpen(!isPiiOpen)}
                className="w-full flex items-center justify-between px-4 py-3 bg-indigo-50/20 hover:bg-indigo-50/40 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <ShieldCheck size={16} className="text-indigo-600 font-bold" />
                  <span className="text-xs font-black text-indigo-900">🔒 個人連絡先・給与振込口座項目 (PII暗号化保護)</span>
                </div>
                <span className="text-[10px] font-bold text-indigo-600 bg-white border border-indigo-200 px-2 py-0.5 rounded-full shadow-sm">
                  {isPiiOpen ? '折りたたむ' : '表示する'}
                </span>
              </button>
              
              {isPiiOpen && (
                <div className="p-4 space-y-4 border-t border-indigo-50 animate-slide-down">
                  <p className="text-[10px] text-indigo-700 font-bold bg-white/80 p-2.5 rounded-xl border border-indigo-100 leading-relaxed shadow-sm">
                    🔒 以下の項目はデータベース上で高度なシステム暗号キーを用いて厳重に保護され、アクセス監査ログの監視下で安全に管理されます。
                  </p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">個人電話番号 (緊急連絡先)</label>
                      <div className="flex items-center gap-2 bg-white border border-slate-100 rounded-xl px-4 py-2.5 focus-within:border-indigo-500 transition-all shadow-inner">
                        <input
                          type="tel"
                          placeholder="例: 090-1234-5678"
                          value={form.personal_phone}
                          onChange={(e) => setForm({ ...form, personal_phone: e.target.value })}
                          className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300 text-xs"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">現住所</label>
                      <div className="flex items-center gap-2 bg-white border border-slate-100 rounded-xl px-4 py-2.5 focus-within:border-indigo-500 transition-all shadow-inner">
                        <input
                          type="text"
                          placeholder="例: 東京都新宿区西新宿1-1-1"
                          value={form.address}
                          onChange={(e) => setForm({ ...form, address: e.target.value })}
                          className="bg-transparent border-0 outline-none w-full text-slate-800 font-bold placeholder-slate-300 text-xs"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">給与振込先金融機関口座情報</label>
                    <div className="flex items-center gap-2 bg-white border border-slate-100 rounded-xl px-4 py-2.5 focus-within:border-indigo-500 transition-all shadow-inner">
                      <input
                        type="text"
                        placeholder="例: ○○銀行 ○○支店 普通 1234567 ナマエ タロウ"
                        value={form.bank_account_info}
                        onChange={(e) => setForm({ ...form, bank_account_info: e.target.value })}
                        className="bg-transparent border-0 outline-none w-full text-slate-850 font-bold placeholder-slate-300 text-xs"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* 有効状態トグル */}
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-2xl border border-slate-100">
              <input
                type="checkbox"
                id="is_active_checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                className="w-5 h-5 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 cursor-pointer"
              />
              <label htmlFor="is_active_checkbox" className="text-sm font-bold text-slate-700 cursor-pointer select-none">
                このスタッフアカウントを有効にする（無効時はシステムにログインできません）
              </label>
            </div>
          </div>

          {/* セクションB: 🔒 システム操作権限（セキュリティ・ロール） */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center gap-2 pb-1 border-b border-slate-50">
              <ShieldCheck size={16} className="text-indigo-500 font-bold" />
              <h3 className="text-sm font-black text-slate-800">2. システム操作権限 (3区分・横並び選択式)</h3>
            </div>
            
            <div className="space-y-3">
              <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">付与するアクセス権限（各レイヤーで選択）</label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* ① システム操作権限 */}
                {(() => {
                  const sysRole = roles.find(r => r.scope === 'SYSTEM');
                  const sysValue = sysRole && form.role_ids.includes(sysRole.id) ? sysRole.id : 0;
                  const isDisabled = loginUserRole !== 'SYSTEM';
                  return (
                    <div className="flex flex-col gap-1.5 border border-slate-100/80 bg-slate-50/20 rounded-2xl p-4 shadow-sm">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <Server size={12} className="text-indigo-500" />
                        システム操作権限
                      </span>
                      <select
                        value={sysValue}
                        disabled={isDisabled}
                        onChange={(e) => handleLayerRoleChange('SYSTEM', Number(e.target.value))}
                        className="w-full text-xs font-bold text-slate-800 bg-white border border-slate-200 rounded-xl px-3 py-2 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer shadow-sm"
                      >
                        <option value="0">なし (権限なし)</option>
                        {sysRole && <option value={sysRole.id}>{sysRole.name}</option>}
                      </select>
                      <span className="text-[9px] text-slate-400 font-bold mt-1">システム全体の管理・保守権限</span>
                    </div>
                  );
                })()}

                {/* ② 法人操作権限 */}
                {(() => {
                  const corpRole = roles.find(r => r.scope === 'CORPORATE');
                  const corpValue = corpRole && form.role_ids.includes(corpRole.id) ? corpRole.id : 0;
                  const isDisabled = loginUserRole !== 'SYSTEM' && loginUserRole !== 'CORPORATE';
                  return (
                    <div className="flex flex-col gap-1.5 border border-slate-100/80 bg-slate-50/20 rounded-2xl p-4 shadow-sm">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <Building2 size={12} className="text-indigo-500" />
                        法人操作権限
                      </span>
                      <select
                        value={corpValue}
                        disabled={isDisabled}
                        onChange={(e) => handleLayerRoleChange('CORPORATE', Number(e.target.value))}
                        className="w-full text-xs font-bold text-slate-800 bg-white border border-slate-200 rounded-xl px-3 py-2 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer shadow-sm"
                      >
                        <option value="0">なし (権限なし)</option>
                        {corpRole && <option value={corpRole.id}>{corpRole.name}</option>}
                      </select>
                      <span className="text-[9px] text-slate-400 font-bold mt-1">法人および全傘下事業所の管理権限</span>
                    </div>
                  );
                })()}

                {/* ③ 事業所操作権限 */}
                {(() => {
                  const jobRole = roles.find(r => r.scope === 'JOB');
                  const staffRole = roles.find(r => r.scope === 'STAFF');
                  const jobValue = jobRole && form.role_ids.includes(jobRole.id) 
                    ? jobRole.id 
                    : (staffRole && form.role_ids.includes(staffRole.id) ? staffRole.id : 0);
                  const isDisabled = loginUserRole === 'NONE';
                  return (
                    <div className="flex flex-col gap-1.5 border border-slate-100/80 bg-slate-50/20 rounded-2xl p-4 shadow-sm">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <Briefcase size={12} className="text-indigo-500" />
                        事業所操作権限
                      </span>
                      <select
                        value={jobValue}
                        disabled={isDisabled}
                        onChange={(e) => handleLayerRoleChange('JOB_LAYER', Number(e.target.value))}
                        className="w-full text-xs font-bold text-slate-800 bg-white border border-slate-200 rounded-xl px-3 py-2 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer shadow-sm"
                      >
                        <option value="0">なし (ログイン不可)</option>
                        {staffRole && <option value={staffRole.id}>{staffRole.name} (一般業務)</option>}
                        {jobRole && <option value={jobRole.id}>{jobRole.name} (事業所管理)</option>}
                      </select>
                      <span className="text-[9px] text-slate-400 font-bold mt-1">所属事業所の操作権限（標準：一般支援員）</span>
                    </div>
                  );
                })()}
              </div>
              <p className="text-[10px] text-slate-400 font-medium leading-relaxed mt-1">
                ※セキュリティ保護のため、ログイン中の管理者が持っていない上位の操作権限を他のスタッフに付与することはできません（特権昇格防止ブロック適用中）。デフォルトは一番下の権限（一般支援員）となっております。
              </p>
            </div>
          </div>

          {/* セクションC: 💼 福祉法令上の職務 ＆ 兼務設定 */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center gap-2 pb-1 border-b border-slate-50">
              <Briefcase size={16} className="text-indigo-500 font-bold" />
              <h3 className="text-sm font-black text-slate-800">3. 福祉法令上の職務設定 (常勤換算FTE用)</h3>
            </div>

            {/* メイン職種セレクトボックス */}
            {!form.is_multiple_jobs && (
              <div className="space-y-3 animate-fade-in">
                <div className="space-y-2">
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest font-bold">メインの実務職務</label>
                  <select
                    value={form.main_job_title_id}
                    onChange={(e) => setForm({ ...form, main_job_title_id: parseInt(e.target.value) })}
                    className="w-full bg-slate-50 border border-slate-100 rounded-2xl px-4 py-3 text-slate-800 font-bold outline-none cursor-pointer focus:border-indigo-500 focus:bg-white border-2"
                  >
                    {jobTitles.map(t => (
                      <option key={t.id} value={t.id}>{t.title_name}</option>
                    ))}
                  </select>
                </div>

                {/* 単一職種時のサビ管みなし配置 */}
                <div className="flex flex-wrap items-center gap-4 bg-slate-50/50 p-3 border border-slate-100 rounded-xl">
                  <label className="flex items-center gap-2 cursor-pointer select-none text-[11px] font-bold text-slate-650">
                    <input
                      type="checkbox"
                      checked={form.main_is_deemed_assignment}
                      onChange={(e) => setForm({ ...form, main_is_deemed_assignment: e.target.checked })}
                      className="w-3.5 h-3.5 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 cursor-pointer"
                    />
                    <span>サービス管理責任者のみなし配置を適用</span>
                  </label>
                  
                  {form.main_is_deemed_assignment && (
                    <div className="flex items-center gap-2 animate-fade-in">
                      <span className="text-[10px] font-bold text-slate-400">みなし期限:</span>
                      <input
                        type="date"
                        value={form.main_deemed_expiry_date}
                        onChange={(e) => setForm({ ...form, main_deemed_expiry_date: e.target.value })}
                        className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-[10px] text-slate-700 font-bold outline-none cursor-pointer focus:border-indigo-500"
                      />
                    </div>
                  )}
                </div>

                <p className="text-[10px] text-slate-400 font-bold">
                  💡 単一職種のため、契約時間（週 {contractHours} 時間）の100%がこの職種に自動で割り当てられます。
                </p>
              </div>
            )}

            {/* 兼務切り替えトグルスイッチ */}
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100">
              <div>
                <label className="text-sm font-black text-slate-700 block cursor-pointer select-none">
                  複数職種での兼務を設定する
                </label>
                <span className="text-[10px] text-slate-400 font-bold">
                  同一事業所内で複数の職種（例：生活支援員と就労支援員）を掛け持つ場合にONにします
                </span>
              </div>
              <input
                type="checkbox"
                id="is_multiple_jobs_checkbox"
                checked={form.is_multiple_jobs}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setForm(prev => ({
                    ...prev,
                    is_multiple_jobs: checked,
                    // トグルONにした時に初期配列を詰める
                    job_assignments: checked 
                      ? [{ job_title_id: prev.main_job_title_id > 0 ? prev.main_job_title_id : (jobTitles[0]?.id || 1), hours: String(contractHours), is_deemed_assignment: false, deemed_expiry_date: '' }]
                      : prev.job_assignments
                  }));
                }}
                className="w-10 h-5 text-indigo-600 border-slate-300 rounded-full focus:ring-indigo-500 cursor-pointer"
              />
            </div>

            {/* 複数職種割り当て（兼務ON時） */}
            {form.is_multiple_jobs && (
              <div className="space-y-4 p-4 border border-indigo-50 bg-indigo-50/10 rounded-2xl animate-slide-down">
                <div className="flex items-center justify-between border-b border-indigo-50/30 pb-2">
                  <span className="text-xs font-black text-indigo-900">兼務職種および週割り当て時間</span>
                  <button
                    type="button"
                    onClick={handleAddJobAssignment}
                    className="flex items-center gap-1 text-[11px] font-black text-indigo-600 hover:text-indigo-800 bg-white border border-indigo-200 px-3 py-1.5 rounded-xl transition-all shadow-sm"
                  >
                    <Plus size={12} />
                    <span>職種を追加</span>
                  </button>
                </div>

                <div className="space-y-3">
                  {form.job_assignments.map((assignment, index) => (
                    <div key={index} className="space-y-2 border border-slate-100 p-3 rounded-xl bg-white/50 animate-fade-in">
                      <div className="flex items-center gap-3">
                        <select
                          value={assignment.job_title_id}
                          onChange={(e) => handleJobAssignmentChange(index, 'job_title_id', e.target.value)}
                          className="flex-1 bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-800 font-bold outline-none cursor-pointer"
                        >
                          {jobTitles.map(t => (
                            <option key={t.id} value={t.id}>{t.title_name}</option>
                          ))}
                        </select>

                        <div className="w-32 flex items-center gap-2 bg-white border border-slate-200 rounded-xl px-3 py-1">
                          <input
                            type="number"
                            step="0.5"
                            placeholder="0"
                            value={assignment.hours}
                            onChange={(e) => handleJobAssignmentChange(index, 'hours', e.target.value)}
                            className="bg-transparent border-0 outline-none w-full text-right text-xs font-bold text-slate-800"
                          />
                          <span className="text-slate-400 text-xs font-bold">時間</span>
                        </div>

                        {form.job_assignments.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveJobAssignment(index)}
                            className="w-9 h-9 rounded-lg hover:bg-rose-50 text-slate-400 hover:text-rose-600 flex items-center justify-center transition-colors shrink-0"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>

                      {/* サビ管みなし設定（チェックボックスと期限） */}
                      <div className="flex flex-wrap items-center gap-4 pt-1.5 px-1 border-t border-dashed border-slate-100">
                        <label className="flex items-center gap-2 cursor-pointer select-none text-[11px] font-bold text-slate-600">
                          <input
                            type="checkbox"
                            checked={!!assignment.is_deemed_assignment}
                            onChange={(e) => handleJobAssignmentChange(index, 'is_deemed_assignment', e.target.checked)}
                            className="w-3.5 h-3.5 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500 cursor-pointer"
                          />
                          <span>サービス管理責任者のみなし配置を適用</span>
                        </label>
                        
                        {assignment.is_deemed_assignment && (
                          <div className="flex items-center gap-2 animate-fade-in">
                            <span className="text-[10px] font-bold text-slate-400">みなし期限:</span>
                            <input
                              type="date"
                              value={assignment.deemed_expiry_date || ''}
                              onChange={(e) => handleJobAssignmentChange(index, 'deemed_expiry_date', e.target.value)}
                              className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-[10px] text-slate-700 font-bold outline-none cursor-pointer focus:border-indigo-500"
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* リアルタイム時間集計インジケータ */}
                <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-slate-500">週割り当て合計 / 週契約労働時間:</span>
                    <span className={`font-mono text-sm ${isHoursMismatch ? 'text-rose-600 font-black' : 'text-indigo-600'}`}>
                      {assignedHoursSum.toFixed(1)} / {contractHours.toFixed(1)} 時間
                    </span>
                  </div>

                  {/* 進捗バー表示 */}
                  <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-300 ${isHoursMismatch ? 'bg-rose-500' : 'bg-indigo-600'}`}
                      style={{ width: `${Math.min(100, (assignedHoursSum / (contractHours || 1)) * 100)}%` }}
                    />
                  </div>

                  {/* 警告メッセージ */}
                  {isHoursMismatch && (
                    <div className="bg-rose-50/50 border border-rose-100 text-[10px] text-rose-700 px-3 py-2 rounded-xl font-bold">
                      ⚠️ 各職種の合計割り当て時間が、週契約労働時間を超えています。登録するには時間を調整するか、下記の「複数事業間重複計上（特例）」をONにしてください。
                    </div>
                  )}
                </div>

                {/* 重複計上例外特例チェックボックス */}
                <div className="pt-2 border-t border-slate-100">
                  <div className="flex items-start gap-3 p-3 bg-indigo-50/30 rounded-xl border border-indigo-100/50 cursor-pointer">
                    <input
                      type="checkbox"
                      id="allow_overlap_checkbox"
                      checked={form.allow_overlap_calculation}
                      onChange={(e) => setForm({ ...form, allow_overlap_calculation: e.target.checked })}
                      className="w-4 h-4 text-indigo-600 border-indigo-300 rounded focus:ring-indigo-500 cursor-pointer mt-0.5"
                    />
                    <div className="select-none">
                      <label htmlFor="allow_overlap_checkbox" className="text-[11px] font-black text-indigo-900 cursor-pointer flex items-center gap-1">
                        <span>複数事業・職種間での重複計上（特例・例外）を適用する</span>
                        <HelpCircle size={12} className="text-indigo-400" />
                      </label>
                      <p className="text-[9px] text-indigo-700 font-bold mt-1 leading-relaxed">
                        ※多機能型事業所や一体型運営（例：就労移行＋就労定着）において、配置基準上、同一の勤務時間内に複数の事業の職務を兼務し、重複して時間を計上することが特例で認められている職員の場合のみONにしてください。ONの間は合計時間の超過制限が解除されます。
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* セクションD: 📅 曜日別契約シフトパターン */}
          <div className="space-y-4 pt-2 border-t border-slate-50">
            <div className="flex items-center gap-2 pb-1">
              <Calendar size={16} className="text-indigo-500 font-bold" />
              <h3 className="text-sm font-black text-slate-800">4. 曜日別契約シフト設定（常勤換算・予実用）</h3>
            </div>

            {/* シフト設定トグル */}
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100">
              <div>
                <label className="text-sm font-black text-slate-700 block cursor-pointer select-none">
                  曜日別契約シフトパターンを設定する
                </label>
                <span className="text-[10px] text-slate-400 font-bold">
                  常勤換算（FTE）の自動配置計算や、曜日ごとの所定労働時間を定義します
                </span>
              </div>
              <input
                type="checkbox"
                id="is_shift_pattern_enabled_checkbox"
                checked={form.is_shift_pattern_enabled}
                onChange={(e) => setForm({ ...form, is_shift_pattern_enabled: e.target.checked })}
                className="w-5 h-5 text-indigo-600 border-slate-300 rounded cursor-pointer"
              />
            </div>

            {/* 曜日別シフトテーブル */}
            {form.is_shift_pattern_enabled && (
              <div className="space-y-4 p-4 border border-indigo-50 bg-indigo-50/10 rounded-2xl animate-slide-down">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-indigo-50/30">
                        <th className="py-2 text-[10px] font-black text-indigo-900 uppercase">曜日</th>
                        <th className="py-2 text-[10px] font-black text-indigo-900 uppercase text-center">稼働</th>
                        <th className="py-2 text-[10px] font-black text-indigo-900 uppercase">始業時間</th>
                        <th className="py-2 text-[10px] font-black text-indigo-900 uppercase">終業時間</th>
                        <th className="py-2 text-[10px] font-black text-indigo-900 uppercase text-center">休憩(分)</th>
                        <th className="py-2 text-[10px] font-black text-indigo-900 uppercase text-right">実働</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-indigo-50/30">
                      {form.shift_patterns.map((pattern, idx) => {
                        const dailyWork = calculateShiftWorkingHours(pattern);
                        const dayLabel = DAYS_OF_WEEK.find(d => d.key === pattern.day_of_week)?.label || pattern.day_of_week;
                        
                        return (
                          <tr key={pattern.day_of_week} className="hover:bg-indigo-50/20 transition-colors">
                            <td className="py-2 text-xs font-bold text-slate-700">{dayLabel}</td>
                            <td className="py-2 text-center">
                              <input
                                type="checkbox"
                                checked={pattern.is_active}
                                onChange={(e) => {
                                  const updated = [...form.shift_patterns];
                                  updated[idx].is_active = e.target.checked;
                                  setForm({ ...form, shift_patterns: updated });
                                }}
                                className="w-4 h-4 text-indigo-600 rounded cursor-pointer"
                              />
                            </td>
                            <td className="py-2">
                              <input
                                type="time"
                                disabled={!pattern.is_active}
                                value={pattern.start_time}
                                onChange={(e) => {
                                  const updated = [...form.shift_patterns];
                                  updated[idx].start_time = e.target.value;
                                  setForm({ ...form, shift_patterns: updated });
                                }}
                                className="bg-white border border-slate-200 rounded-lg px-1.5 py-1 text-xs font-bold outline-none disabled:opacity-40"
                              />
                            </td>
                            <td className="py-2">
                              <input
                                type="time"
                                disabled={!pattern.is_active}
                                value={pattern.end_time}
                                onChange={(e) => {
                                  const updated = [...form.shift_patterns];
                                  updated[idx].end_time = e.target.value;
                                  setForm({ ...form, shift_patterns: updated });
                                }}
                                className="bg-white border border-slate-200 rounded-lg px-1.5 py-1 text-xs font-bold outline-none disabled:opacity-40"
                              />
                            </td>
                            <td className="py-2 text-center">
                              <input
                                type="number"
                                disabled={!pattern.is_active}
                                value={pattern.break_minutes}
                                step="10"
                                min="0"
                                onChange={(e) => {
                                  const updated = [...form.shift_patterns];
                                  updated[idx].break_minutes = parseInt(e.target.value) || 0;
                                  setForm({ ...form, shift_patterns: updated });
                                }}
                                className="w-16 bg-white border border-slate-200 rounded-lg px-1.5 py-1 text-xs font-bold text-center outline-none disabled:opacity-40"
                              />
                            </td>
                            <td className="py-2 text-right text-xs font-mono font-bold text-slate-600">
                              {pattern.is_active ? `${dailyWork.toFixed(1)}h` : '--'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* リアルタイム週シフト合計時間 ＆ 契約時間差異チェック */}
                <div className="pt-2 border-t border-slate-100 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-slate-500">週シフト実働合計 / 週契約労働時間:</span>
                    <span className={`font-mono text-sm ${isShiftHoursMismatch ? 'text-amber-600 font-bold' : 'text-indigo-600'}`}>
                      {totalShiftWorkingHours.toFixed(1)} / {contractHours.toFixed(1)} 時間
                    </span>
                  </div>

                  {/* 差異がある場合のマイルドな親切警告 */}
                  {isShiftHoursMismatch && (
                    <div className="bg-amber-50 border border-amber-100 text-[10px] text-amber-800 p-2.5 rounded-xl font-bold leading-normal">
                      💡 曜日別シフトの実働合計（{totalShiftWorkingHours.toFixed(1)}時間）が、週契約時間（{contractHours.toFixed(1)}時間）と一致していません。
                      実務上の一時的な不規則勤務でない場合は、契約時間またはシフト時間をご確認ください。
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* アクションボタン */}
          <div className="pt-6 flex gap-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-200 hover:bg-slate-50 text-slate-500 font-black py-4 px-6 rounded-2xl transition-all text-sm"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isSaving || isHoursMismatch}
              className="flex-1 bg-gradient-to-tr from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-black py-4 px-6 rounded-2xl shadow-lg hover:shadow-xl transition-all disabled:opacity-40 flex items-center justify-center gap-2 text-sm"
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
