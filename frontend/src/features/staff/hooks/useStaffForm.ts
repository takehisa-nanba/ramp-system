import { useState, useEffect } from 'react';
import type { StaffMember, Role, JobTitle } from '../types';
import { useAuth } from '../../../context/AuthContext';

const DAYS_OF_WEEK = [
  { key: 'Monday', label: '月曜日' },
  { key: 'Tuesday', label: '火曜日' },
  { key: 'Wednesday', label: '水曜日' },
  { key: 'Thursday', label: '木曜日' },
  { key: 'Friday', label: '金曜日' },
  { key: 'Saturday', label: '土曜日' },
  { key: 'Sunday', label: '日曜日' }
];

export const useStaffForm = (
  isOpen: boolean,
  mode: 'create' | 'edit',
  staff: StaffMember | null,
  roles: Role[],
  jobTitles: JobTitle[]
) => {
  const getInitialFormState = () => ({
    last_name: '',
    first_name: '',
    last_name_kana: '',
    first_name_kana: '',
    staff_code: '',
    email: '',
    employment_type: 'FULL_TIME',
    password: '',
    hire_date: new Date().toISOString().split('T')[0],
    retirement_date: '',
    weekly_scheduled_hours: '40',
    is_active: true,
    role_ids: [] as number[],
    
    // 暗号化個人情報 (PII)
    personal_phone: '',
    address: '',
    bank_account_info: '',
    
    // 実務職務設定用
    main_job_title_id: jobTitles[0]?.id || 0,
    main_is_deemed_assignment: false,
    main_deemed_expiry_date: '',
    is_multiple_jobs: false,
    allow_overlap_calculation: false,
    job_assignments: [] as { job_title_id: number; hours: string; is_deemed_assignment?: boolean; deemed_expiry_date?: string }[],

    // 曜日別契約シフト設定用
    is_shift_pattern_enabled: false,
    shift_patterns: DAYS_OF_WEEK.map(d => ({
      day_of_week: d.key,
      start_time: '09:00',
      end_time: '18:00',
      break_minutes: 60,
      is_active: false
    }))
  });

  const [form, setForm] = useState(getInitialFormState());
  const [validationError, setValidationError] = useState<string | null>(null);

  const { user } = useAuth();

  // ログインユーザーの最高セキュリティ・ロールを判定
  const getLoginUserMaxRole = (): 'SYSTEM' | 'CORPORATE' | 'JOB' | 'NONE' => {
    try {
      const scopes = user?.roleScopes || [];
      
      if (scopes.includes('SYSTEM')) return 'SYSTEM';
      if (scopes.includes('CORPORATE')) return 'CORPORATE';
      if (scopes.includes('JOB')) return 'JOB';
      return 'NONE';
    } catch {
      return 'NONE';
    }
  };

  const loginUserRole = getLoginUserMaxRole();

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

  useEffect(() => {
    if (isOpen) {
      if (mode === 'edit' && staff) {
        // Edit mode initial population
        const hasShiftPatterns = !!(staff.shift_patterns && staff.shift_patterns.length > 0);
        
        const mergedShiftPatterns = DAYS_OF_WEEK.map(d => {
          const existing = (staff.shift_patterns || []).find(p => p.day_of_week === d.key);
          if (existing) {
            return {
              day_of_week: existing.day_of_week,
              start_time: existing.start_time || '09:00',
              end_time: existing.end_time || '18:00',
              break_minutes: existing.break_minutes,
              is_active: true
            };
          }
          return {
            day_of_week: d.key,
            start_time: '09:00',
            end_time: '18:00',
            break_minutes: 60,
            is_active: false
          };
        });

        // 職務割り当てのパース
        const assignments = staff.job_assignments || [];
        const isMulti = assignments.length > 1;
        const mainAssign = assignments.length > 0 ? assignments[0] : null;
        
        setForm({
          last_name: staff.last_name,
          first_name: staff.first_name,
          last_name_kana: staff.last_name_kana,
          first_name_kana: staff.first_name_kana,
          staff_code: staff.staff_code,
          email: staff.email || '',
          employment_type: staff.employment_type || 'FULL_TIME',
          password: '',
          hire_date: staff.hire_date ? staff.hire_date.split('T')[0] : '',
          retirement_date: staff.retirement_date ? staff.retirement_date.split('T')[0] : '',
          weekly_scheduled_hours: staff.weekly_scheduled_minutes ? (staff.weekly_scheduled_minutes / 60).toString() : '40',
          is_active: staff.is_active,
          role_ids: staff.role_ids || [],
          
          personal_phone: staff.personal_phone || '',
          address: staff.address || '',
          bank_account_info: staff.bank_account_info || '',
          
          main_job_title_id: mainAssign ? mainAssign.job_title_id : (jobTitles[0]?.id || 0),
          main_is_deemed_assignment: mainAssign ? !!mainAssign.is_deemed_assignment : false,
          main_deemed_expiry_date: mainAssign && mainAssign.deemed_expiry_date ? mainAssign.deemed_expiry_date.split('T')[0] : '',
          
          is_multiple_jobs: isMulti,
          allow_overlap_calculation: !!staff.allow_overlap_calculation,
          job_assignments: assignments.map(a => ({
            job_title_id: a.job_title_id,
            hours: (a.assigned_minutes / 60).toString(),
            is_deemed_assignment: a.is_deemed_assignment,
            deemed_expiry_date: a.deemed_expiry_date ? a.deemed_expiry_date.split('T')[0] : undefined
          })),

          is_shift_pattern_enabled: hasShiftPatterns,
          shift_patterns: mergedShiftPatterns
        });
      } else {
        // Create mode
        const defaultJobId = jobTitles[0]?.id || 0;
        const staffRole = roles.find(r => r.scope === 'STAFF');
        const defaultRoleIds = staffRole ? [staffRole.id] : [];
        const initialState = getInitialFormState();

        setForm({
          ...initialState,
          main_job_title_id: defaultJobId,
          role_ids: defaultRoleIds,
          job_assignments: [{ job_title_id: defaultJobId, hours: '40' }],
        });
      }
      setValidationError(null);
    }
  }, [isOpen, mode, staff, jobTitles, roles]);

  return {
    form,
    setForm,
    validationError,
    setValidationError,
    loginUserRole,
    handleLayerRoleChange,
    DAYS_OF_WEEK
  };
};
