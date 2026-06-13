import React, { useEffect, useMemo, useState } from 'react';
import { Building2, Save, ShieldCheck, UserCog, Plus, X, RefreshCw } from 'lucide-react';
import { managementApi, type JobAssignment, type JobTitle, type ManagementMasters, type OfficeSettings, type Role, type StaffMember, type OfficeService } from '../services/managementApi';
import { toKatakana } from '../utils/inputHelpers';
import { useAuth } from '../context/AuthContext';
import { useMessage } from '../context/MessageContext';
import { useAutoKana } from '../hooks/useAutoKana';
import { UXField, PostalAddressField } from '../components/common/UXFields';
import { Heading, Text, Label } from '../components/common/Typography';

type TabKey = 'office' | 'staff';

type StaffForm = {
  id?: number;
  staff_code: string;
  last_name: string;
  first_name: string;
  last_name_kana: string;
  first_name_kana: string;
  email: string;
  personal_phone: string;
  address: string;
  employment_type: string;
  weekly_scheduled_minutes: number;
  hire_date: string;
  retirement_date: string;
  is_active: boolean;
  allow_overlap_calculation: boolean;
  role_ids: number[];
  job_assignments: JobAssignment[];
};

const EMPTY_STAFF_FORM: StaffForm = {
  staff_code: '',
  last_name: '',
  first_name: '',
  last_name_kana: '',
  first_name_kana: '',
  email: '',
  personal_phone: '',
  address: '',
  employment_type: 'FULL_TIME',
  weekly_scheduled_minutes: 2400,
  hire_date: new Date().toISOString().slice(0, 10),
  retirement_date: '',
  is_active: true,
  allow_overlap_calculation: false,
  role_ids: [],
  job_assignments: []
};

const employmentTypeLabels: Record<string, string> = {
  FULL_TIME: '常勤',
  SHORTENED_FT: '短時間常勤',
  PART_TIME: '非常勤',
  CONTRACT: '契約職員'
};

const disabilityKeys = [
  ['physical', '身体'],
  ['intellectual', '知的'],
  ['mental', '精神'],
  ['developmental', '発達'],
  ['intractable', '難病']
] as const;

const minutesToHoursText = (minutes?: number) => `${((minutes || 0) / 60).toFixed(1)}h`;

const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const { showSuccess } = useMessage();

  const [postalCode, setPostalCode] = useState('');

  const lastNameAuto = useAutoKana('', '', {
    onValueChange: (val) => updateStaffForm('last_name', val),
    onKanaChange: (kana) => updateStaffForm('last_name_kana', kana),
  });
  const firstNameAuto = useAutoKana('', '', {
    onValueChange: (val) => updateStaffForm('first_name', val),
    onKanaChange: (kana) => updateStaffForm('first_name_kana', kana),
  });
  
  const isManager = useMemo(() => {
    return user?.roleScopes?.some(scope => ['SYSTEM', 'CORPORATE', 'JOB'].includes(scope)) ?? false;
  }, [user]);

  const hasViewStaff = useMemo(() => {
    if (user?.permissions) {
      return user.permissions.includes('VIEW_STAFF');
    }
    return isManager;
  }, [user, isManager]);

  const hasCreateStaff = useMemo(() => {
    if (user?.permissions) {
      return user.permissions.includes('CREATE_STAFF');
    }
    return isManager;
  }, [user, isManager]);

  const hasEditStaff = useMemo(() => {
    if (user?.permissions) {
      return user.permissions.includes('EDIT_STAFF');
    }
    return isManager;
  }, [user, isManager]);

  const [activeTab, setActiveTab] = useState<TabKey>('office');
  const [office, setOffice] = useState<OfficeSettings | null>(null);
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [jobTitles, setJobTitles] = useState<JobTitle[]>([]);
  const [masters, setMasters] = useState<ManagementMasters | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [officeError, setOfficeError] = useState<string | null>(null);
  const [officeMessage, setOfficeMessage] = useState<string | null>(null);
  const [staffModalError, setStaffModalError] = useState<string | null>(null);
  const [staffForm, setStaffForm] = useState<StaffForm | null>(null);
  const [fullTimeWeeklyHoursText, setFullTimeWeeklyHoursText] = useState<string>('');
  const [weeklyScheduledHoursText, setWeeklyScheduledHoursText] = useState<string>('');

  useEffect(() => {
    if (!hasViewStaff && activeTab === 'staff') {
      setActiveTab('office');
    }
  }, [hasViewStaff, activeTab]);

  const loadAll = async () => {
    setLoading(true);
    setGeneralError(null);
    try {
      const [officeRes, staffRes, rolesRes, jobTitlesRes, mastersRes] = await Promise.all([
        managementApi.getOfficeSettings(),
        managementApi.getStaffMembers(),
        managementApi.getAvailableRoles(),
        managementApi.getJobTitles(),
        managementApi.getMasters()
      ]);
      setOffice(officeRes);
      setFullTimeWeeklyHoursText(officeRes.full_time_weekly_minutes ? String(officeRes.full_time_weekly_minutes / 60) : '40');
      setStaff(staffRes);
      setRoles(rolesRes);
      setJobTitles(jobTitlesRes);
      setMasters(mastersRes);
    } catch (err: any) {
      setGeneralError(err?.response?.data?.error?.message || err?.message || '設定情報の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const staffOptions = useMemo(() => staff.map((s) => ({ id: s.id, name: s.name })), [staff]);

  const saveOffice = async () => {
    if (!office) return;
    if (!office.services || office.services.length === 0) {
      setOfficeError('提供サービスは最低1つ登録する必要があります。');
      return;
    }
    const selectedTypes = office.services.map((s) => s.service_type_master_id);
    if (selectedTypes.length !== new Set(selectedTypes).size) {
      setOfficeError('同じサービス種別を複数登録することはできません。');
      return;
    }

    setSaving(true);
    setOfficeError(null);
    setOfficeMessage(null);
    try {
      const hours = parseFloat(fullTimeWeeklyHoursText) || 0;
      const payload: OfficeSettings = {
        ...office,
        full_time_weekly_minutes: Math.round(hours * 60)
      };
      await managementApi.updateOfficeSettings(payload);
      setOfficeMessage('事業者・事業所・サービス設定を保存しました。');
      await loadAll();
    } catch (err: any) {
      setOfficeError(err?.response?.data?.error?.message || err?.message || '保存に失敗しました。');
    } finally {
      setSaving(false);
    }
  };

  const openStaffForm = (member?: StaffMember) => {
    setGeneralError(null);
    setStaffModalError(null);
    setPostalCode('');
    if (!member) {
      setStaffForm({
        ...EMPTY_STAFF_FORM,
        role_ids: []
      });
      setWeeklyScheduledHoursText(String(EMPTY_STAFF_FORM.weekly_scheduled_minutes / 60));
      lastNameAuto.reset();
      firstNameAuto.reset();
      return;
    }
    setStaffForm({
      id: member.id,
      staff_code: member.staff_code,
      last_name: member.last_name,
      first_name: member.first_name,
      last_name_kana: member.last_name_kana,
      first_name_kana: member.first_name_kana,
      email: member.email || '',
      personal_phone: member.personal_phone || '',
      address: member.address || '',
      employment_type: member.employment_type || 'FULL_TIME',
      weekly_scheduled_minutes: member.weekly_scheduled_minutes || 0,
      hire_date: member.hire_date || '',
      retirement_date: member.retirement_date || '',
      is_active: member.is_active,
      allow_overlap_calculation: member.allow_overlap_calculation,
      role_ids: member.role_ids || [],
      job_assignments: member.job_assignments?.length ? member.job_assignments.map((j) => ({ ...j, assigned_hours_text: String((j.assigned_minutes || 0) / 60) })) : []
    });
    setWeeklyScheduledHoursText(String((member.weekly_scheduled_minutes || 0) / 60));

    lastNameAuto.setValue(member.last_name || '');
    lastNameAuto.setKana(member.last_name_kana || '');
    lastNameAuto.setIsManual(!!member.last_name_kana);
    firstNameAuto.setValue(member.first_name || '');
    firstNameAuto.setKana(member.first_name_kana || '');
    firstNameAuto.setIsManual(!!member.first_name_kana);
  };

  const saveStaff = async () => {
    if (!staffForm) return;
    setSaving(true);
    setStaffModalError(null);
    try {
      const hours = parseFloat(weeklyScheduledHoursText) || 0;
      const payload = {
        ...staffForm,
        weekly_scheduled_minutes: Math.round(hours * 60),
        last_name_kana: toKatakana(staffForm.last_name_kana),
        first_name_kana: toKatakana(staffForm.first_name_kana),
        retirement_date: staffForm.retirement_date || null,
        job_assignments: staffForm.job_assignments
          .filter((j) => j.job_title_id && j.assigned_minutes > 0)
          .map(({ assigned_hours_text, ...rest }) => rest)
      };
      if (staffForm.id) {
        await managementApi.updateStaff(staffForm.id, payload);
        showSuccess('職員設定を更新しました。');
      } else {
        await managementApi.registerStaff(payload);
        showSuccess('職員を登録しました。');
      }
      setStaffForm(null);
      await loadAll();
    } catch (err: any) {
      setStaffModalError(err?.response?.data?.error?.message || err?.message || '職員設定の保存に失敗しました。');
    } finally {
      setSaving(false);
    }
  };

  const updateOffice = (key: keyof OfficeSettings, value: any) => {
    setOffice((prev) => prev ? { ...prev, [key]: value } : prev);
  };

  const updateServiceItem = (index: number, patch: Partial<OfficeService>) => {
    setOffice((prev) => {
      if (!prev || !prev.services) return prev;
      const nextServices = [...prev.services];
      nextServices[index] = { ...nextServices[index], ...patch };
      return { ...prev, services: nextServices };
    });
  };

  const handleServiceTypeChangeForIndex = (index: number, serviceTypeMasterId: number) => {
    if (!office || !masters || !office.services) return;
    
    const selectedService = masters.service_types.find((s) => s.id === serviceTypeMasterId);
    let patch: Partial<OfficeService> = { service_type_master_id: serviceTypeMasterId };
    
    if (selectedService) {
      switch (selectedService.service_code) {
        case 'TRANSITION': // 就労移行支援
        case 'CONTINUOUS_B': // 就労継続支援B型
        case 'RETENTION': // 就労定着支援
        case 'SELECTION': // 就労選択支援
          patch.capacity = 20;
          patch.target_disabilities = {
            physical: true,
            intellectual: true,
            mental: true,
            developmental: true,
            intractable: true
          };
          break;
        case 'CONTINUOUS_A': // 就労継続支援A型
          patch.capacity = 10;
          patch.target_disabilities = {
            physical: true,
            intellectual: true,
            mental: true,
            developmental: true,
            intractable: true
          };
          break;
        case 'TRAINING': // 自立訓練（生活訓練）
          patch.capacity = 20;
          patch.target_disabilities = {
            physical: false,
            intellectual: true,
            mental: true,
            developmental: true,
            intractable: true
          };
          break;
      }
    }
    updateServiceItem(index, patch);
  };

  const addServiceItem = () => {
    if (!office || !masters) return;
    const defaultServiceId = masters.service_types[0]?.id || 1;
    const newService: OfficeService = {
      service_type_master_id: defaultServiceId,
      jigyosho_bango: '',
      capacity: 20,
      manager_supporter_id: null,
      target_disabilities: {
        physical: true,
        intellectual: true,
        mental: true,
        developmental: true,
        intractable: true
      }
    };
    
    const selectedService = masters.service_types.find((s) => s.id === defaultServiceId);
    if (selectedService) {
      switch (selectedService.service_code) {
        case 'CONTINUOUS_A':
          newService.capacity = 10;
          break;
        case 'TRAINING':
          newService.target_disabilities = {
            physical: false,
            intellectual: true,
            mental: true,
            developmental: true,
            intractable: true
          };
          break;
      }
    }
    
    setOffice((prev) => {
      if (!prev) return prev;
      const services = prev.services ? [...prev.services, newService] : [newService];
      return { ...prev, services };
    });
  };

  const removeServiceItem = (index: number) => {
    setOffice((prev) => {
      if (!prev || !prev.services) return prev;
      const services = prev.services.filter((_, i) => i !== index);
      return { ...prev, services };
    });
  };

  const updateStaffForm = (key: keyof StaffForm, value: any) => {
    setStaffForm((prev) => prev ? { ...prev, [key]: value } : prev);
  };

  const handleRoleScopeChange = (scope: 'CORPORATE' | 'JOB' | 'SYSTEM', targetRoleId: number | '') => {
    setStaffForm((prev) => {
      if (!prev) return prev;
      const otherScopeRoleIds = prev.role_ids.filter((id) => {
        const r = roles.find((role) => role.id === id);
        return r && r.scope !== scope;
      });
      const newRoleIds = [...otherScopeRoleIds];
      if (targetRoleId !== '') {
        newRoleIds.push(targetRoleId);
      }
      return { ...prev, role_ids: newRoleIds };
    });
  };

  const addJobAssignment = () => {
    const defaultHours = parseFloat(weeklyScheduledHoursText) || 0;
    setStaffForm((prev) => prev ? {
      ...prev,
      job_assignments: [...prev.job_assignments, { job_title_id: jobTitles[0]?.id || 0, assigned_minutes: Math.round(defaultHours * 60), assigned_hours_text: String(defaultHours), is_deemed_assignment: false }]
    } : prev);
  };

  const updateJobAssignment = (index: number, patch: Partial<JobAssignment & { assigned_hours_text: string }>) => {
    setStaffForm((prev) => {
      if (!prev) return prev;
      const next = [...prev.job_assignments];
      const newPatch = { ...patch };
      if ('assigned_hours_text' in patch) {
        const hours = parseFloat(patch.assigned_hours_text || '') || 0;
        newPatch.assigned_minutes = Math.round(hours * 60);
      }
      next[index] = { ...next[index], ...newPatch };
      return { ...prev, job_assignments: next };
    });
  };

  const removeJobAssignment = (index: number) => {
    setStaffForm((prev) => prev ? { ...prev, job_assignments: prev.job_assignments.filter((_, i) => i !== index) } : prev);
  };

  const assignedMinutesTotal = staffForm?.job_assignments.reduce((sum, j) => sum + (Number(j.assigned_minutes) || 0), 0) || 0;

  if (loading) {
    return <div className="p-6 text-slate-500 font-bold">設定を読み込み中...</div>;
  }

  return (
    <div className="px-4 pb-8 md:px-8 md:pb-12 space-y-6">
      <div className="sticky top-0 z-10 bg-white/90 backdrop-blur-md pt-6 pb-4 md:pt-8 md:pb-4 mb-6 border-b border-slate-200 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-[10px] md:text-xs font-black tracking-[0.25em] text-indigo-500 uppercase">RAMP Skeleton Settings</p>
          <Heading variant="h1" className="mt-1">基本設定</Heading>
          <Text variant="small" className="mt-2">法人・事業所・職員・職務を定義し、支援サイクルが乗る骨格を作ります。</Text>
        </div>
        <button onClick={loadAll} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 font-bold hover:bg-slate-50">
          <RefreshCw size={16} /> 再読み込み
        </button>
      </div>

      {generalError && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
          {generalError}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
          <div className="flex items-center gap-3"><Building2 className="text-indigo-500" /><span className="font-black text-slate-800">骨格</span></div>
          <p className="text-xs text-slate-500 mt-2">法人・事業所・サービス提供単位</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
          <div className="flex items-center gap-3"><UserCog className="text-indigo-500" /><span className="font-black text-slate-800">職務</span></div>
          <p className="text-xs text-slate-500 mt-2">職員に付与される文脈と責務</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
          <div className="flex items-center gap-3"><ShieldCheck className="text-indigo-500" /><span className="font-black text-slate-800">観測可能性</span></div>
          <p className="text-xs text-slate-500 mt-2">権限境界と意思決定の前提を残す</p>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="flex border-b border-slate-100">
          <button onClick={() => setActiveTab('office')} className={`px-5 py-4 text-sm font-black ${activeTab === 'office' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-400'}`}>事業者・事業所</button>
          {hasViewStaff && (
            <button onClick={() => setActiveTab('staff')} className={`px-5 py-4 text-sm font-black ${activeTab === 'staff' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-400'}`}>職員・職務</button>
          )}
        </div>

        {activeTab === 'office' && office && (
          <div className="p-5 lg:p-8 space-y-8">
            {(officeMessage || officeError) && (
              <div className={`rounded-2xl border px-4 py-3 text-sm font-bold ${officeError ? 'bg-rose-50 border-rose-200 text-rose-700' : 'bg-emerald-50 border-emerald-200 text-emerald-700'}`}>
                {officeError || officeMessage}
              </div>
            )}
            <SectionTitle title="法人設定" description="契約主体・テナントとしての法人情報" />
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Field label="法人名" value={office.corporation_name || ''} onChange={(v) => updateOffice('corporation_name', v)} />
              <Field label="法人種別" value={office.corporation_type || ''} onChange={(v) => updateOffice('corporation_type', v)} placeholder="株式会社 / NPO法人 など" />
              <Field label="法人番号" value={office.corporation_number || ''} onChange={(v) => updateOffice('corporation_number', v)} />
              <Field label="代表者名" value={office.corporation_representative_name || ''} onChange={(v) => updateOffice('corporation_representative_name', v)} />
              <Field label="法人郵便番号" value={office.corporation_postal_code || ''} onChange={(v) => updateOffice('corporation_postal_code', v)} />
              <Field label="法人電話番号" value={office.corporation_phone_number || ''} onChange={(v) => updateOffice('corporation_phone_number', v)} />
              <Field className="md:col-span-2" label="法人所在地" value={office.corporation_address || ''} onChange={(v) => updateOffice('corporation_address', v)} />
              <Field label="テナントID" value={office.tenant_id || ''} onChange={(v) => updateOffice('tenant_id', v)} />
            </div>

            <SectionTitle title="事業所設定" description="勤務・配置・監査の基準となる事業所情報" />
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <Field label="事業所名" value={office.office_name || ''} onChange={(v) => updateOffice('office_name', v)} />
              <SelectField label="所在自治体" value={office.municipality_id || ''} onChange={(v) => updateOffice('municipality_id', Number(v) || undefined)}>
                <option value="">未設定</option>
                {masters?.municipalities.map((m) => <option key={m.id} value={m.id}>{m.city_name} {m.city_code ? `(${m.city_code})` : ''}</option>)}
              </SelectField>
              <Field label="常勤週所定時間" type="number" value={fullTimeWeeklyHoursText} onChange={(v) => setFullTimeWeeklyHoursText(v)} />
              <Field label="郵便番号" value={office.postal_code || ''} onChange={(v) => updateOffice('postal_code', v)} />
              <Field label="電話番号" value={office.phone_number || ''} onChange={(v) => updateOffice('phone_number', v)} />
              <Field label="FAX" value={office.fax_number || ''} onChange={(v) => updateOffice('fax_number', v)} />
              <Field className="md:col-span-2" label="所在地" value={office.address || ''} onChange={(v) => updateOffice('address', v)} />
              <Field label="メール" value={office.email_address || ''} onChange={(v) => updateOffice('email_address', v)} />
              <Field label="事業所代表者" value={office.representative_name || ''} onChange={(v) => updateOffice('representative_name', v)} />
            </div>

            <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <SectionTitle title="サービス設定" description="受給者証・請求・配置基準と接続する提供サービス" />
              <button type="button" onClick={addServiceItem} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-black hover:bg-indigo-700">
                <Plus size={16} /> サービスを追加
              </button>
            </div>

            <div className="space-y-6 mt-4">
              {office.services?.map((service, index) => (
                <div key={index} className="bg-slate-50 p-5 rounded-2xl border border-slate-200 relative space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-lg text-xs font-bold">
                      サービス #{index + 1}
                    </span>
                    <button type="button" onClick={() => removeServiceItem(index)} className="text-rose-500 hover:text-rose-700 text-sm font-bold flex items-center gap-1">
                      <X size={16} /> 削除
                    </button>
                  </div>
                  
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <SelectField label="サービス種別" value={service.service_type_master_id || ''} onChange={(v) => handleServiceTypeChangeForIndex(index, Number(v))}>
                      <option value="">未設定</option>
                      {masters?.service_types.map((s) => <option key={s.id} value={s.id}>{s.service_name} {s.service_code ? `(${s.service_code})` : ''}</option>)}
                    </SelectField>
                    
                    <Field label="事業所番号" value={service.jigyosho_bango || ''} onChange={(v) => updateServiceItem(index, { jigyosho_bango: v })} placeholder="10桁の事業所番号" />
                    
                    <Field label="定員" type="number" value={service.capacity || 0} onChange={(v) => updateServiceItem(index, { capacity: Number(v) })} />
                    
                    <Field label="サービス提供開始時刻" type="time" value={service.default_start_time || ''} onChange={(v) => updateServiceItem(index, { default_start_time: v })} />
                    
                    <Field label="サービス提供終了時刻" type="time" value={service.default_end_time || ''} onChange={(v) => updateServiceItem(index, { default_end_time: v })} />
                    
                    <SelectField label="サービス管理責任者" value={service.manager_supporter_id || ''} onChange={(v) => updateServiceItem(index, { manager_supporter_id: Number(v) || null })}>
                      <option value="">未設定</option>
                      {staffOptions.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                    </SelectField>
                    
                    <Field label="初回指定年月日" type="date" value={service.initial_designation_date || ''} onChange={(v) => updateServiceItem(index, { initial_designation_date: v })} />
                    
                    <Field label="指定有効期限" type="date" value={service.designation_expiry_date || ''} onChange={(v) => updateServiceItem(index, { designation_expiry_date: v })} />
                    
                    <Field label="地域区分" value={service.regional_category || ''} onChange={(v) => updateServiceItem(index, { regional_category: v })} placeholder="例: 1級地" />
                    
                    <div className="md:col-span-2 lg:col-span-3">
                      <label className="block text-xs font-black text-slate-500 mb-2">主たる対象者</label>
                      <div className="flex flex-wrap gap-2">
                        {disabilityKeys.map(([key, label]) => {
                          const checked = !!service.target_disabilities?.[key];
                          return (
                            <button key={key} type="button" onClick={() => updateServiceItem(index, { target_disabilities: { ...(service.target_disabilities || {}), [key]: !checked } })} className={`px-3 py-2 rounded-xl text-xs font-bold border ${checked ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-500 border-slate-200'}`}>
                              {label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    
                    <label className="md:col-span-2 lg:col-span-3 block">
                      <span className="block text-xs font-black text-slate-500 mb-1">協力医療機関</span>
                      <textarea value={service.cooperating_medical_institution || ''} onChange={(e) => updateServiceItem(index, { cooperating_medical_institution: e.target.value })} className="w-full min-h-20 px-3 py-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm" />
                    </label>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end">
              <button onClick={saveOffice} disabled={saving} className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-indigo-600 text-white font-black hover:bg-indigo-700 disabled:opacity-50">
                <Save size={18} /> 保存する
              </button>
            </div>
          </div>
        )}

        {activeTab === 'staff' && (
          <div className="p-5 lg:p-8 space-y-5">
            <div className="flex items-center justify-between gap-3">
              <SectionTitle title="職員・職務設定" description="職員本人ではなく、職員に割り当てられた文脈と責務を管理します。" />
              {hasCreateStaff && (
                <button onClick={() => openStaffForm()} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-black hover:bg-indigo-700"><Plus size={16} /> 職員追加</button>
              )}
            </div>
            <div className="overflow-x-auto rounded-2xl border border-slate-100">
              <table className="min-w-full divide-y divide-slate-100 text-sm">
                <thead className="bg-slate-50 text-xs font-black text-slate-500">
                  <tr>
                    <th className="px-4 py-3 text-left">職員</th>
                    <th className="px-4 py-3 text-left">RAMPロール</th>
                    <th className="px-4 py-3 text-left">職務割当</th>
                    <th className="px-4 py-3 text-left">週所定</th>
                    <th className="px-4 py-3 text-left">状態</th>
                    <th className="px-4 py-3 text-right">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {staff.map((s) => (
                    <tr key={s.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3"><div className="font-black text-slate-800">{s.name}</div><div className="text-xs text-slate-400">{s.staff_code} / {s.email}</div></td>
                      <td className="px-4 py-3"><div className="flex flex-wrap gap-1">{s.roles.map((r) => <span key={r} className="px-2 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-bold">{r}</span>)}</div></td>
                      <td className="px-4 py-3"><div className="space-y-1">{s.job_assignments.map((j) => <div key={`${s.id}-${j.id || j.job_title_id}`} className="text-xs text-slate-600">{j.title_name}: {minutesToHoursText(j.assigned_minutes)}</div>)}</div></td>
                      <td className="px-4 py-3 font-bold text-slate-700">{minutesToHoursText(s.weekly_scheduled_minutes)}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 rounded-lg text-xs font-black ${s.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>{s.is_active ? '有効' : '無効'}</span></td>
                      <td className="px-4 py-3 text-right">
                        {hasEditStaff ? (
                          <button onClick={() => openStaffForm(s)} className="px-3 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-bold">編集</button>
                        ) : (
                          <span className="text-xs text-slate-400 font-bold">閲覧のみ</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {staffForm && (
        <div className="fixed inset-0 z-[100] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto bg-white rounded-3xl shadow-2xl">
            <div className="sticky top-0 bg-white border-b border-slate-100 px-6 py-4 flex items-center justify-between rounded-t-3xl">
              <div><h2 className="text-xl font-black text-slate-900">{staffForm.id ? '職員設定の編集' : '職員の追加'}</h2><p className="text-xs text-slate-500 mt-1">組織・事業所・RAMP運用上の立場を同じ職員に紐づけます。</p></div>
              <button onClick={() => setStaffForm(null)} className="p-2 rounded-xl hover:bg-slate-100"><X size={22} /></button>
            </div>
            {staffModalError && (
              <div className="mx-6 mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-bold text-rose-700">
                {staffModalError}
              </div>
            )}
            <div className="p-6 space-y-7">
              <SectionTitle title="基本情報" description="職員としての識別情報" />
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Field label="職員コード" value={staffForm.staff_code} onChange={(v) => updateStaffForm('staff_code', v)} />
                <UXField label="姓" {...lastNameAuto.inputProps} />
                <UXField label="セイ" {...lastNameAuto.kanaInputProps} />
                <Field label="メール" value={staffForm.email} onChange={(v) => updateStaffForm('email', v)} />
                <UXField label="名" {...firstNameAuto.inputProps} />
                <UXField label="メイ" {...firstNameAuto.kanaInputProps} />
                <Field label="電話" value={staffForm.personal_phone} onChange={(v) => updateStaffForm('personal_phone', v)} />
              </div>

              <PostalAddressField
                postalLabel="郵便番号"
                addressLabel="住所"
                postalValue={postalCode}
                addressValue={staffForm.address}
                onPostalChange={setPostalCode}
                onAddressChange={(v) => updateStaffForm('address', v)}
                className="mt-4"
              />

              <SectionTitle title="雇用・稼働設定" description="常勤換算と配置基準の前提" />
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                <SelectField label="雇用形態" value={staffForm.employment_type} onChange={(v) => updateStaffForm('employment_type', v)}>
                  {Object.entries(employmentTypeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </SelectField>
                <Field label="週所定時間" type="number" value={weeklyScheduledHoursText} onChange={(v) => setWeeklyScheduledHoursText(v)} />
                <Field label="入職日" type="date" value={staffForm.hire_date} onChange={(v) => updateStaffForm('hire_date', v)} />
                <Field label="退職日" type="date" value={staffForm.retirement_date} onChange={(v) => updateStaffForm('retirement_date', v)} />
              </div>
              <div className="flex flex-wrap gap-3">
                <Toggle checked={staffForm.is_active} label="アカウント有効" onChange={(v) => updateStaffForm('is_active', v)} />
                <Toggle checked={staffForm.allow_overlap_calculation} label="複数事業の重複計上特例を許可" onChange={(v) => updateStaffForm('allow_overlap_calculation', v)} />
              </div>

              {/* RAMPロール（階層選択） */}
              {(() => {
                const currentCorpRoleId = staffForm ? (roles.find(r => r.scope === 'CORPORATE' && staffForm.role_ids.includes(r.id))?.id ?? '') : '';
                const currentSysRoleId = staffForm ? (roles.find(r => r.scope === 'SYSTEM' && staffForm.role_ids.includes(r.id))?.id ?? '') : '';

                return (
                  <>
                    <SectionTitle title="権限・ロール設定" description="組織の階層構造（法人 ＞ システム）に応じたシステム管理・監査権限を指定します。" />
                    <div className="grid md:grid-cols-2 gap-4">
                      <SelectField
                        label="1. 法人スコープの役割 (CORPORATE)"
                        value={currentCorpRoleId}
                        onChange={(v) => handleRoleScopeChange('CORPORATE', v ? Number(v) : '')}
                      >
                        <option value="">一般 (デフォルト / 権限なし)</option>
                        {roles.filter(r => r.scope === 'CORPORATE').map(r => (
                          <option key={r.id} value={r.id}>{r.name}</option>
                        ))}
                      </SelectField>

                      <SelectField
                        label="2. システムスコープの役割 (SYSTEM)"
                        value={currentSysRoleId}
                        onChange={(v) => handleRoleScopeChange('SYSTEM', v ? Number(v) : '')}
                      >
                        <option value="">一般 (デフォルト / 権限なし)</option>
                        {roles.filter(r => r.scope === 'SYSTEM').map(r => (
                          <option key={r.id} value={r.id}>{r.name}</option>
                        ))}
                      </SelectField>
                    </div>
                  </>
                );
              })()}

              <SectionTitle title="職務割当" description="誰が、どの職務を、どれだけ担うか。権限境界の中心です。" />
              <div className="space-y-3">
                {staffForm.job_assignments.map((job, index) => (
                  <div key={index} className="grid md:grid-cols-[1fr_160px_140px_48px] gap-3 items-end bg-slate-50 p-3 rounded-2xl">
                    <SelectField label="職務" value={job.job_title_id || ''} onChange={(v) => updateJobAssignment(index, { job_title_id: Number(v) })}>
                      <option value="">選択</option>
                      {jobTitles.map((j) => <option key={j.id} value={j.id}>{j.title_name}</option>)}
                    </SelectField>
                    <Field
                      label="割当時間/週"
                      type="number"
                      value={job.assigned_hours_text ?? ''}
                      onChange={(v) => updateJobAssignment(index, { assigned_hours_text: v })}
                    />
                    <Toggle checked={!!job.is_deemed_assignment} label="みなし配置" onChange={(v) => updateJobAssignment(index, { is_deemed_assignment: v })} />
                    <button onClick={() => removeJobAssignment(index)} className="h-10 rounded-xl bg-white border border-slate-200 text-rose-500 font-black">×</button>
                  </div>
                ))}
                <button onClick={addJobAssignment} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-dashed border-slate-300 text-slate-500 font-bold text-sm hover:bg-slate-50"><Plus size={16} /> 職務を追加</button>
                <div className={`text-sm font-bold ${assignedMinutesTotal > staffForm.weekly_scheduled_minutes && !staffForm.allow_overlap_calculation ? 'text-rose-600' : 'text-slate-500'}`}>職務割当合計: {minutesToHoursText(assignedMinutesTotal)} / 週所定: {minutesToHoursText(staffForm.weekly_scheduled_minutes)}</div>
              </div>
            </div>
            <div className="sticky bottom-0 bg-white border-t border-slate-100 px-6 py-4 flex justify-end gap-3 rounded-b-3xl">
              <button onClick={() => setStaffForm(null)} className="px-4 py-2 rounded-xl bg-slate-100 text-slate-600 font-black">キャンセル</button>
              <button onClick={saveStaff} disabled={saving} className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 text-white font-black disabled:opacity-50"><Save size={18} /> 保存する</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const SectionTitle: React.FC<{ title: string; description?: string }> = ({ title, description }) => (
  <div>
    <Heading variant="h2">{title}</Heading>
    {description && <Text variant="small" className="mt-1">{description}</Text>}
  </div>
);

const Field: React.FC<{ label: string; value: string | number; onChange: (value: string) => void; type?: string; placeholder?: string; className?: string }> = ({ label, value, onChange, type = 'text', placeholder, className = '' }) => (
  <div className={`block ${className}`}>
    <Label variant="form" className="block text-slate-500 mb-1">{label}</Label>
    <input type={type} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} className="w-full h-10 px-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm md:text-base" />
  </div>
);

const SelectField: React.FC<{ label: string; value: string | number; onChange: (value: string) => void; children: React.ReactNode }> = ({ label, value, onChange, children }) => (
  <div className="block">
    <Label variant="form" className="block text-slate-500 mb-1">{label}</Label>
    <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm md:text-base">
      {children}
    </select>
  </div>
);

const Toggle: React.FC<{ checked: boolean; label: string; onChange: (checked: boolean) => void }> = ({ checked, label, onChange }) => (
  <label className="inline-flex items-center gap-2 cursor-pointer">
    <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    <Text variant="small" className="!font-bold">{label}</Text>
  </label>
);

export default SettingsPage;
