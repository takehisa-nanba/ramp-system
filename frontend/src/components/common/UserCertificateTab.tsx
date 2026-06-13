import React, { useState, useEffect } from 'react';
import { Plus, Copy, Save, AlertCircle, FileText, Trash2, Calendar, Edit3 } from 'lucide-react';
import { useMasters } from '../../hooks/useMasters';
import { addServiceCertificate, updateServiceCertificate, submitServiceCertificate, reviewServiceCertificate, voidServiceCertificate, fetchUserPii, updateUserDetails, type ServiceCertificateData } from '../../services/userService';
import { managementApi } from '../../services/managementApi';
import { useAuth } from '../../context/AuthContext';

interface UserCertificateTabProps {
  userId: number;
  certificates: any[];
  onUpdateSuccess: () => void;
}

export const UserCertificateTab: React.FC<UserCertificateTabProps> = ({ userId, certificates, onUpdateSuccess }) => {
  const { masters, loading } = useMasters();
  const { user: currentUser } = useAuth();
  
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [editingCertificateId, setEditingCertificateId] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [userPii, setUserPii] = useState<any>(null);
  const [officeSettings, setOfficeSettings] = useState<any>(null);
  const [isReasonModalOpen, setIsReasonModalOpen] = useState(false);
  const [updateReasonText, setUpdateReasonText] = useState('');
  const [reasonError, setReasonError] = useState<string | null>(null);

  const [targetStatus, setTargetStatus] = useState<'DRAFT' | 'PENDING_REVIEW'>('DRAFT');
  const [reviewComments, setReviewComments] = useState<Record<number, string>>({});
  const [reviewErrors, setReviewErrors] = useState<Record<number, string>>({});

  const [isVoidModalOpen, setIsVoidModalOpen] = useState(false);
  const [voidReasonText, setVoidReasonText] = useState('');
  const [voidTargetCertId, setVoidTargetCertId] = useState<number | null>(null);
  const [voidError, setVoidError] = useState<string | null>(null);

  const isAdmin = !!currentUser?.roleScopes?.some((scope: string) => ['SYSTEM', 'CORPORATE'].includes(scope));

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'DRAFT':
        return <span className="bg-slate-100 text-slate-700 text-[10px] font-black px-2.5 py-1 rounded-full border border-slate-200">下書き</span>;
      case 'PENDING_REVIEW':
        return <span className="bg-amber-100 text-amber-800 text-[10px] font-black px-2.5 py-1 rounded-full border border-amber-200 animate-pulse">確認待ち</span>;
      case 'ACTIVE':
        return <span className="bg-emerald-100 text-emerald-800 text-[10px] font-black px-2.5 py-1 rounded-full border border-emerald-200">有効</span>;
      case 'REJECTED':
        return <span className="bg-rose-100 text-rose-800 text-[10px] font-black px-2.5 py-1 rounded-full border border-rose-200">却下</span>;
      case 'ARCHIVED':
        return <span className="bg-slate-200 text-slate-500 text-[10px] font-black px-2.5 py-1 rounded-full border border-slate-300">アーカイブ済</span>;
      case 'VOIDED':
        return <span className="bg-red-50 text-red-700 text-[10px] font-black px-2.5 py-1 rounded-full border border-red-200">無効化済</span>;
      default:
        return <span className="bg-slate-100 text-slate-700 text-[10px] font-black px-2.5 py-1 rounded-full border border-slate-200">{status}</span>;
    }
  };

  // 利用者基本情報用のローカルステート
  const [basicLastName, setBasicLastName] = useState('');
  const [basicFirstName, setBasicFirstName] = useState('');
  const [basicLastNameKana, setBasicLastNameKana] = useState('');
  const [basicFirstNameKana, setBasicFirstNameKana] = useState('');
  const [basicBirthDate, setBasicBirthDate] = useState('');
  const [basicAddress, setBasicAddress] = useState('');

  const [formData, setFormData] = useState<ServiceCertificateData>({
    certificate_issue_date: '',
    municipality_master_id: 1,
    certificate_type: '障害福祉サービス受給者証',
    disability_support_classification: '',
    recipient_number: '',
    certificate_notes: '',
    office_service_configuration_id: undefined,
    granted_services: [],
    copayment_limits: [
      {
        limit_start_date: '',
        limit_end_date: '',
        limit_amount: 0,
        is_management_required: false
      }
    ],
    meal_addon_statuses: [],
    copayment_managements: [
      {
        management_start_date: '',
        management_end_date: '',
        is_applicable: false,
        managing_office_number: '',
        managing_office_name: ''
      }
    ]
  });

  // Load PII and Office Settings on mount
  useEffect(() => {
    fetchUserPii(userId)
      .then(res => {
        setUserPii(res);
        if (res?.pii) {
          setBasicLastName(res.pii.last_name || '');
          setBasicFirstName(res.pii.first_name || '');
          setBasicLastNameKana(res.pii.last_name_kana || '');
          setBasicFirstNameKana(res.pii.first_name_kana || '');
          setBasicBirthDate(res.pii.birth_date || '');
          setBasicAddress(res.pii.address || '');
        }
      })
      .catch(err => console.error("Error loading user PII:", err));
      
    managementApi.getOfficeSettings()
      .then(settings => setOfficeSettings(settings))
      .catch(err => console.error("Error loading office settings:", err));
  }, [userId]);

  const handleCancel = () => {
    setIsFormVisible(false);
    setEditingCertificateId(null);
    if (userPii?.pii) {
      setBasicLastName(userPii.pii.last_name || '');
      setBasicFirstName(userPii.pii.first_name || '');
      setBasicLastNameKana(userPii.pii.last_name_kana || '');
      setBasicFirstNameKana(userPii.pii.first_name_kana || '');
      setBasicBirthDate(userPii.pii.birth_date || '');
      setBasicAddress(userPii.pii.address || '');
    }
  };

  // 最新の受給者証が存在しない場合、初期表示でフォームを開く
  useEffect(() => {
    if (certificates.length === 0) {
      setIsFormVisible(true);
    }
  }, [certificates]);

  const handleCopy = (cert: any) => {
    setEditingCertificateId(null);
    setFormData({
      certificate_issue_date: '', // 新しい日付を入力してもらうため空に
      municipality_master_id: cert.municipality_master_id,
      certificate_type: cert.certificate_type || '障害福祉サービス受給者証',
      disability_support_classification: cert.disability_support_classification || '',
      recipient_number: cert.recipient_number || '',
      certificate_notes: cert.certificate_notes || '',
      office_service_configuration_id: cert.office_service_configuration_id || undefined,
      granted_services: (cert.granted_services || []).map((g: any) => ({
        service_type_master_id: g.service_type_master_id,
        granted_start_date: g.granted_start_date || '',
        granted_end_date: g.granted_end_date || '',
        granted_amount_description: g.granted_amount_description || '',
        max_service_days: g.max_service_days ?? 23,
        max_service_days_type: g.max_service_days_type || 'FIXED',
        granted_amount_start_date: g.granted_amount_start_date || '',
        granted_amount_end_date: g.granted_amount_end_date || '',
        contract_detail: g.contract_detail ? {
          office_service_configuration_id: g.contract_detail.office_service_configuration_id,
          contract_granted_days: g.contract_detail.contract_granted_days ?? 23,
          contract_date: g.contract_detail.contract_date || '',
          contract_end_date: g.contract_detail.contract_end_date || '',
          contract_end_used_days: g.contract_detail.contract_end_used_days ?? 0,
          contract_document_url: g.contract_detail.contract_document_url || '',
          important_matters_url: g.contract_detail.important_matters_url || ''
        } : {
          office_service_configuration_id: officeSettings?.services?.[0]?.id || 1,
          contract_granted_days: g.max_service_days ?? 23,
          contract_date: g.granted_start_date || '',
          contract_end_date: '',
          contract_end_used_days: 0,
          contract_document_url: '',
          important_matters_url: ''
        }
      })),
      copayment_limits: cert.copayment_limits && cert.copayment_limits.length > 0 ? (cert.copayment_limits || []).map((cl: any) => ({
        limit_start_date: cl.limit_start_date || '',
        limit_end_date: cl.limit_end_date || '',
        limit_amount: cl.limit_amount ?? 0,
        is_management_required: cl.is_management_required ?? false
      })) : [{
        limit_start_date: '',
        limit_end_date: '',
        limit_amount: 0,
        is_management_required: false
      }],
      meal_addon_statuses: (cert.meal_addon_statuses || []).map((ma: any) => ({
        meal_addon_start_date: ma.meal_addon_start_date || '',
        meal_addon_end_date: ma.meal_addon_end_date || '',
        is_applicable: ma.is_applicable ?? false
      })),
      copayment_managements: cert.copayment_managements && cert.copayment_managements.length > 0 ? (cert.copayment_managements || []).map((cm: any) => ({
        management_start_date: cm.management_start_date || '',
        management_end_date: cm.management_end_date || '',
        is_applicable: cm.is_applicable ?? false,
        managing_office_number: cm.managing_office_number || '',
        managing_office_name: cm.managing_office_name || ''
      })) : [{
        management_start_date: '',
        management_end_date: '',
        is_applicable: false,
        managing_office_number: '',
        managing_office_name: ''
      }]
    });
    setIsFormVisible(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleEdit = (cert: any) => {
    setEditingCertificateId(cert.id);
    setFormData({
      certificate_issue_date: cert.certificate_issue_date || '',
      municipality_master_id: cert.municipality_master_id,
      certificate_type: cert.certificate_type || '障害福祉サービス受給者証',
      disability_support_classification: cert.disability_support_classification || '',
      recipient_number: cert.recipient_number || '',
      certificate_notes: cert.certificate_notes || '',
      office_service_configuration_id: cert.office_service_configuration_id || undefined,
      granted_services: (cert.granted_services || []).map((g: any) => ({
        service_type_master_id: g.service_type_master_id,
        granted_start_date: g.granted_start_date || '',
        granted_end_date: g.granted_end_date || '',
        granted_amount_description: g.granted_amount_description || '',
        max_service_days: g.max_service_days ?? 23,
        max_service_days_type: g.max_service_days_type || 'FIXED',
        granted_amount_start_date: g.granted_amount_start_date || '',
        granted_amount_end_date: g.granted_amount_end_date || '',
        contract_detail: g.contract_detail ? {
          office_service_configuration_id: g.contract_detail.office_service_configuration_id,
          contract_granted_days: g.contract_detail.contract_granted_days ?? 23,
          contract_date: g.contract_detail.contract_date || '',
          contract_end_date: g.contract_detail.contract_end_date || '',
          contract_end_used_days: g.contract_detail.contract_end_used_days ?? 0,
          contract_document_url: g.contract_detail.contract_document_url || '',
          important_matters_url: g.contract_detail.important_matters_url || ''
        } : {
          office_service_configuration_id: officeSettings?.services?.[0]?.id || 1,
          contract_granted_days: g.max_service_days ?? 23,
          contract_date: g.granted_start_date || '',
          contract_end_date: '',
          contract_end_used_days: 0,
          contract_document_url: '',
          important_matters_url: ''
        }
      })),
      copayment_limits: cert.copayment_limits && cert.copayment_limits.length > 0 ? (cert.copayment_limits || []).map((cl: any) => ({
        limit_start_date: cl.limit_start_date || '',
        limit_end_date: cl.limit_end_date || '',
        limit_amount: cl.limit_amount ?? 0,
        is_management_required: cl.is_management_required ?? false
      })) : [{
        limit_start_date: '',
        limit_end_date: '',
        limit_amount: 0,
        is_management_required: false
      }],
      meal_addon_statuses: (cert.meal_addon_statuses || []).map((ma: any) => ({
        meal_addon_start_date: ma.meal_addon_start_date || '',
        meal_addon_end_date: ma.meal_addon_end_date || '',
        is_applicable: ma.is_applicable ?? false
      })),
      copayment_managements: cert.copayment_managements && cert.copayment_managements.length > 0 ? (cert.copayment_managements || []).map((cm: any) => ({
        management_start_date: cm.management_start_date || '',
        management_end_date: cm.management_end_date || '',
        is_applicable: cm.is_applicable ?? false,
        managing_office_number: cm.managing_office_number || '',
        managing_office_name: cm.managing_office_name || ''
      })) : [{
        management_start_date: '',
        management_end_date: '',
        is_applicable: false,
        managing_office_number: '',
        managing_office_name: ''
      }]
    });
    setIsFormVisible(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNew = () => {
    setEditingCertificateId(null);
    setFormData({
      certificate_issue_date: '',
      municipality_master_id: masters?.municipalities[0]?.id || 1,
      certificate_type: '障害福祉サービス受給者証',
      disability_support_classification: '',
      recipient_number: '',
      certificate_notes: '',
      office_service_configuration_id: officeSettings?.services?.[0]?.id || undefined,
      granted_services: [],
      copayment_limits: [
        {
          limit_start_date: '',
          limit_end_date: '',
          limit_amount: 0,
          is_management_required: false
        }
      ],
      meal_addon_statuses: [],
      copayment_managements: [
        {
          management_start_date: '',
          management_end_date: '',
          is_applicable: false,
          managing_office_number: '',
          managing_office_name: ''
        }
      ]
    });
    setIsFormVisible(true);
  };

  const addGrantedService = () => {
    setFormData(prev => ({
      ...prev,
      granted_services: [
        ...prev.granted_services,
        {
          service_type_master_id: masters?.service_types[0]?.id || 1,
          granted_start_date: '',
          granted_end_date: '',
          granted_amount_description: '',
          max_service_days: 23,
          max_service_days_type: 'DYNAMIC_MONTH_MINUS_8',
          granted_amount_start_date: '',
          granted_amount_end_date: '',
          contract_detail: {
            office_service_configuration_id: officeSettings?.services?.[0]?.id || 1,
            contract_granted_days: 23,
            contract_date: '',
            contract_end_date: '',
            contract_end_used_days: 0,
            contract_document_url: '',
            important_matters_url: ''
          }
        }
      ]
    }));
  };

  const removeGrantedService = (index: number) => {
    setFormData(prev => ({
      ...prev,
      granted_services: prev.granted_services.filter((_, i) => i !== index)
    }));
  };

  const updateGrantedService = (index: number, field: string, value: any) => {
    setFormData(prev => {
      const gs = [...prev.granted_services];
      let service = { ...gs[index], [field]: value };
      
      // 有効期間・契約日は原則支給決定期間と同一の値で初期化・同期するが、個別に編集可能
      if (field === 'granted_start_date') {
        service.granted_amount_start_date = value;
        if (service.contract_detail) {
          service.contract_detail = {
            ...service.contract_detail,
            contract_date: value
          };
        }
      } else if (field === 'granted_end_date') {
        service.granted_amount_end_date = value;
      }
      
      gs[index] = service;

      // 最初の支給決定期間の変更に合わせて、負担上限額や上限管理、食事提供加算の有効期間もデフォルト同期する（個別に編集可能）
      let cls = [...(prev.copayment_limits || [])];
      let cmg = [...(prev.copayment_managements || [])];
      let mas = [...(prev.meal_addon_statuses || [])];

      if (index === 0) {
        if (field === 'granted_start_date') {
          if (cls[0]) {
            cls[0] = { ...cls[0], limit_start_date: value };
          }
          if (cmg[0]) {
            cmg[0] = { ...cmg[0], management_start_date: value };
          }
          if (mas[0]) {
            mas[0] = { ...mas[0], meal_addon_start_date: value };
          }
        } else if (field === 'granted_end_date') {
          if (cls[0]) {
            cls[0] = { ...cls[0], limit_end_date: value };
          }
          if (cmg[0]) {
            cmg[0] = { ...cmg[0], management_end_date: value };
          }
          if (mas[0]) {
            mas[0] = { ...mas[0], meal_addon_end_date: value };
          }
        }
      }

      return {
        ...prev,
        granted_services: gs,
        copayment_limits: cls,
        copayment_managements: cmg,
        meal_addon_statuses: mas
      };
    });
  };

  // Unused because copayment limits addition/deletion buttons are removed per requirement.

  const updateCopaymentLimit = (index: number, field: string, value: any) => {
    setFormData(prev => {
      const cls = [...(prev.copayment_limits || [])];
      cls[index] = { ...cls[index], [field]: value };
      
      let cmg = [...(prev.copayment_managements || [])];
      if (field === 'is_management_required') {
        if (value) {
          if (!cmg[index]) {
            cmg[index] = {
              management_start_date: cls[index].limit_start_date,
              management_end_date: cls[index].limit_end_date,
              is_applicable: true,
              managing_office_number: '',
              managing_office_name: ''
            };
          } else {
            cmg[index] = {
              ...cmg[index],
              is_applicable: true,
              management_start_date: cmg[index].management_start_date || cls[index].limit_start_date,
              management_end_date: cmg[index].management_end_date || cls[index].limit_end_date
            };
          }
        } else {
          if (cmg[index]) {
            cmg[index] = { ...cmg[index], is_applicable: false };
          }
        }
      } else if (field === 'limit_start_date' || field === 'limit_end_date') {
        if (cmg[index]) {
          cmg[index] = {
            ...cmg[index],
            management_start_date: field === 'limit_start_date' ? value : cmg[index].management_start_date,
            management_end_date: field === 'limit_end_date' ? value : cmg[index].management_end_date
          };
        }
      }
      return { ...prev, copayment_limits: cls, copayment_managements: cmg };
    });
  };

  const addMealAddonStatus = () => {
    setFormData(prev => ({
      ...prev,
      meal_addon_statuses: [
        ...(prev.meal_addon_statuses || []),
        {
          meal_addon_start_date: '',
          meal_addon_end_date: '',
          is_applicable: true
        }
      ]
    }));
  };

  const removeMealAddonStatus = (index: number) => {
    setFormData(prev => ({
      ...prev,
      meal_addon_statuses: (prev.meal_addon_statuses || []).filter((_, i) => i !== index)
    }));
  };

  const updateMealAddonStatus = (index: number, field: string, value: any) => {
    setFormData(prev => {
      const mas = [...(prev.meal_addon_statuses || [])];
      mas[index] = { ...mas[index], [field]: value };
      return { ...prev, meal_addon_statuses: mas };
    });
  };

  const handleSaveClick = (status: 'DRAFT' | 'PENDING_REVIEW') => {
    setTargetStatus(status);
    if (!formData.certificate_issue_date) {
      setError('交付年月日は必須です');
      return;
    }
    // 支給決定サービスおよび契約情報の必須チェック
    if (!formData.granted_services || formData.granted_services.length === 0) {
      setError('支給決定サービス内容を少なくとも1件以上追加してください。');
      return;
    }
    for (const g of formData.granted_services) {
      const serviceName = masters?.service_types.find(s => s.id === g.service_type_master_id)?.service_name || `ID:${g.service_type_master_id}`;
      if (!g.granted_start_date || !g.granted_end_date) {
        setError(`決定期間の開始日・終了日を入力してください (${serviceName})。`);
        return;
      }
      if (g.max_service_days_type === 'FIXED' && (g.max_service_days === undefined || g.max_service_days === null || isNaN(g.max_service_days))) {
        setError(`「原則の日数を適用する」がオフの場合、支給上限日数の入力は必須です (${serviceName})。`);
        return;
      }
      const cd = g.contract_detail;
      if (!cd || !cd.office_service_configuration_id || !cd.contract_date) {
        setError(`契約情報（契約事業所サービス、契約日）の入力は必須です (${serviceName})。`);
        return;
      }
      if (cd.contract_granted_days === undefined || cd.contract_granted_days === null || isNaN(cd.contract_granted_days)) {
        setError(`契約支給量（原則の日数）を入力してください (${serviceName})。`);
        return;
      }
    }

    // 負担上限額の必須チェック
    if (!formData.copayment_limits || formData.copayment_limits.length === 0) {
      setError('利用者負担上限額の設定は必須です。');
      return;
    }
    const cl = formData.copayment_limits[0];
    if (!cl.limit_start_date || !cl.limit_end_date) {
      setError('負担上限額の適用期間（開始日・終了日）を入力してください。');
      return;
    }
    if (cl.is_management_required) {
      const cm = formData.copayment_managements?.[0];
      if (!cm || !cm.managing_office_number || !cm.managing_office_name || !cm.management_start_date || !cm.management_end_date) {
        setError('上限管理ありの場合、管理事業所番号、管理事業所名、管理期間（開始日・終了日）の入力はすべて必須です。');
        return;
      }
      if (cm.managing_office_number.length !== 10) {
        setError('管理事業所番号は10桁で入力してください。');
        return;
      }
    }

    setError(null);
    if (editingCertificateId) {
      setIsReasonModalOpen(true);
    } else {
      handleSubmit(status);
    }
  };

  const handleReasonSubmit = () => {
    setReasonError(null);
    setIsReasonModalOpen(false);
    handleSubmit(targetStatus, updateReasonText.trim() || '受給者証の更新');
  };

  const handleSubmit = async (status: 'DRAFT' | 'PENDING_REVIEW', reason?: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      // 1. まず利用者の基本情報を更新
      await updateUserDetails(userId, {
        display_name: `${basicLastName} ${basicFirstName}`,
        pii: {
          last_name: basicLastName,
          first_name: basicFirstName,
          last_name_kana: basicLastNameKana,
          first_name_kana: basicFirstNameKana,
          birth_date: basicBirthDate || null,
          address: basicAddress
        }
      });

      // 2. 次に受給者証情報を保存
      const updatedGrantedServices = formData.granted_services.map(g => {
        const desc = g.max_service_days_type === 'DYNAMIC_MONTH_MINUS_8'
          ? '原則の日数（月－8日）'
          : `${g.max_service_days}日/月`;
        return {
          ...g,
          granted_amount_description: desc
        };
      });

      const payload = {
        ...formData,
        status: status,
        granted_services: updatedGrantedServices,
        update_reason: reason
      };
      if (editingCertificateId) {
        await updateServiceCertificate(userId, editingCertificateId, payload);
      } else {
        await addServiceCertificate(userId, payload);
      }

      // 3. PIIを再取得してローカル状態を更新
      const updatedPii = await fetchUserPii(userId);
      setUserPii(updatedPii);
      if (updatedPii?.pii) {
        setBasicLastName(updatedPii.pii.last_name || '');
        setBasicFirstName(updatedPii.pii.first_name || '');
        setBasicLastNameKana(updatedPii.pii.last_name_kana || '');
        setBasicFirstNameKana(updatedPii.pii.first_name_kana || '');
        setBasicBirthDate(updatedPii.pii.birth_date || '');
        setBasicAddress(updatedPii.pii.address || '');
      }

      setIsFormVisible(false);
      setEditingCertificateId(null);
      setUpdateReasonText('');
      onUpdateSuccess(); // リストを再取得
    } catch (err: any) {
      setError(err.response?.data?.msg || '保存に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitReview = async (certId: number) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await submitServiceCertificate(userId, certId);
      onUpdateSuccess();
    } catch (err: any) {
      setError(err.response?.data?.msg || '申請に失敗しました。');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReview = async (certId: number, action: 'approve' | 'reject', reviewReason?: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await reviewServiceCertificate(userId, certId, action, reviewReason);
      onUpdateSuccess();
    } catch (err: any) {
      setError(err.response?.data?.msg || '確認・承認に失敗しました。');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReviewAction = async (certId: number, action: 'approve' | 'reject') => {
    const comment = reviewComments[certId] || '';
    if (action === 'reject' && !comment.trim()) {
      setReviewErrors(prev => ({ ...prev, [certId]: '却下理由は必須です' }));
      return;
    }
    setReviewErrors(prev => ({ ...prev, [certId]: '' }));
    await handleReview(certId, action, comment);
    setReviewComments(prev => ({ ...prev, [certId]: '' }));
  };

  const handleVoidClick = (certId: number) => {
    setVoidTargetCertId(certId);
    setVoidReasonText('');
    setVoidError(null);
    setIsVoidModalOpen(true);
  };

  const handleVoidSubmit = async () => {
    if (!voidTargetCertId) return;
    if (!voidReasonText.trim()) {
      setVoidError('無効化の理由を入力してください。');
      return;
    }
    setIsSubmitting(true);
    setVoidError(null);
    try {
      await voidServiceCertificate(userId, voidTargetCertId, voidReasonText);
      setIsVoidModalOpen(false);
      setVoidReasonText('');
      setVoidTargetCertId(null);
      onUpdateSuccess();
    } catch (err: any) {
      console.error("Error voiding certificate:", err);
      setVoidError(err.response?.data?.msg || '無効化処理に失敗しました。');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400 text-xs font-bold animate-pulse">マスターデータを読み込み中...</div>;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* --- エラー表示 --- */}
      {error && (
        <div className="bg-rose-50 text-rose-600 p-3 rounded-xl text-xs font-bold flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* --- 新規作成 / コピー編集フォーム --- */}
      {isFormVisible && (
        <div className="bg-indigo-50/50 border border-indigo-100 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-indigo-100 pb-3">
            <h3 className="text-sm font-black text-indigo-900 flex items-center gap-2">
              <FileText size={16} className="text-indigo-500" />
              {editingCertificateId ? '受給者証情報の修正' : '受給者証情報の入力'}
            </h3>
          </div>

          {/* 基本情報 (入力/編集可能) */}
          <div className="bg-white border border-slate-100 rounded-xl p-4 space-y-4 shadow-sm">
            <div className="text-[11px] font-black text-indigo-900 uppercase tracking-wider border-b border-slate-100 pb-1.5 flex items-center gap-1.5">
              <span>👤 利用者基本情報 (変更すると基本情報マスタも更新されます)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">氏名 (漢字)</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="姓"
                    value={basicLastName}
                    onChange={e => setBasicLastName(e.target.value)}
                    className="w-1/2 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
                  />
                  <input
                    type="text"
                    placeholder="名"
                    value={basicFirstName}
                    onChange={e => setBasicFirstName(e.target.value)}
                    className="w-1/2 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">氏名 (かな)</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="せい"
                    value={basicLastNameKana}
                    onChange={e => setBasicLastNameKana(e.target.value)}
                    className="w-1/2 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
                  />
                  <input
                    type="text"
                    placeholder="めい"
                    value={basicFirstNameKana}
                    onChange={e => setBasicFirstNameKana(e.target.value)}
                    className="w-1/2 bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">生年月日</span>
                <input
                  type="date"
                  value={basicBirthDate}
                  onChange={e => setBasicBirthDate(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
                />
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">住所</span>
              <input
                type="text"
                placeholder="住所を入力してください"
                value={basicAddress}
                onChange={e => setBasicAddress(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
              />
            </div>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">交付年月日 *</label>
              <input
                type="date"
                value={formData.certificate_issue_date}
                onChange={e => setFormData({ ...formData, certificate_issue_date: e.target.value })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">発行自治体</label>
              <select
                value={formData.municipality_master_id}
                onChange={e => setFormData({ ...formData, municipality_master_id: Number(e.target.value) })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              >
                {masters?.municipalities.map(m => (
                  <option key={m.id} value={m.id}>{m.city_name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">証の種別</label>
              <input
                type="text"
                value={formData.certificate_type}
                onChange={e => setFormData({ ...formData, certificate_type: e.target.value })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">障害支援区分</label>
              <select
                value={formData.disability_support_classification}
                onChange={e => setFormData({ ...formData, disability_support_classification: e.target.value })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              >
                <option value="">未設定</option>
                <option value="区分1">区分1</option>
                <option value="区分2">区分2</option>
                <option value="区分3">区分3</option>
                <option value="区分4">区分4</option>
                <option value="区分5">区分5</option>
                <option value="区分6">区分6</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">受給者証番号 (10桁)</label>
              <input
                type="text"
                maxLength={10}
                value={formData.recipient_number || ''}
                onChange={e => setFormData({ ...formData, recipient_number: e.target.value })}
                placeholder="例: 1310100012"
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">管理事業所サービス</label>
              <select
                value={formData.office_service_configuration_id || ''}
                onChange={e => setFormData({ ...formData, office_service_configuration_id: e.target.value ? Number(e.target.value) : undefined })}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
              >
                <option value="">未設定</option>
                {officeSettings?.services?.map((s: any) => {
                  const sName = masters?.service_types.find(st => st.id === s.service_type_master_id)?.service_name || `ID:${s.service_type_master_id}`;
                  return <option key={s.id} value={s.id}>{officeSettings.office_name} - {sName}</option>;
                })}
              </select>
            </div>
          </div>
          
          <div className="space-y-1.5">
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">特記事項</label>
            <input
              type="text"
              value={formData.certificate_notes}
              onChange={e => setFormData({ ...formData, certificate_notes: e.target.value })}
              className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold"
            />
          </div>

          {/* 支給決定サービス内容 */}
          <div className="pt-4 border-t border-indigo-100">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-black text-slate-700">支給決定サービス内容と契約情報</h4>
              <button onClick={addGrantedService} className="text-[10px] font-bold text-indigo-600 bg-indigo-100 hover:bg-indigo-200 px-2 py-1 rounded-lg flex items-center gap-1 transition-colors">
                <Plus size={12} /> 追加
              </button>
            </div>
            
            <div className="space-y-4">
              {formData.granted_services.map((g, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
                  <div className="flex flex-wrap sm:flex-nowrap gap-3 items-end">
                    <div className="w-full sm:w-1/3 space-y-1">
                      <label className="text-[10px] font-black text-slate-400">サービス種別</label>
                      <select
                        value={g.service_type_master_id}
                        onChange={e => updateGrantedService(idx, 'service_type_master_id', Number(e.target.value))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      >
                        {masters?.service_types.map(s => (
                          <option key={s.id} value={s.id}>{s.service_name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="w-full sm:w-1/3 space-y-1">
                      <label className="text-[10px] font-black text-slate-400">決定期間 開始日</label>
                      <input
                        type="date"
                        value={g.granted_start_date}
                        onChange={e => updateGrantedService(idx, 'granted_start_date', e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      />
                    </div>
                    <div className="w-full sm:w-1/3 space-y-1">
                      <label className="text-[10px] font-black text-slate-400">決定期間 終了日</label>
                      <input
                        type="date"
                        value={g.granted_end_date}
                        onChange={e => updateGrantedService(idx, 'granted_end_date', e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      />
                    </div>
                    <button onClick={() => removeGrantedService(idx)} className="h-[28px] w-[28px] shrink-0 flex items-center justify-center text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg mb-[2px]">
                      <Trash2 size={14} />
                    </button>
                  </div>

                  {/* 支給上限計算設定 & 支給量有効期間 */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50/50 p-3 rounded-lg border border-slate-100">
                    <div className="space-y-1 flex items-center h-full pt-4">
                      <label className="flex items-center gap-2 text-[10px] font-black text-slate-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={g.max_service_days_type === 'DYNAMIC_MONTH_MINUS_8'}
                          onChange={e => {
                            const isDynamic = e.target.checked;
                            updateGrantedService(idx, 'max_service_days_type', isDynamic ? 'DYNAMIC_MONTH_MINUS_8' : 'FIXED');
                            if (isDynamic) {
                              updateGrantedService(idx, 'max_service_days', null);
                            }
                          }}
                          className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        原則の日数（月 - 8日）を適用する
                      </label>
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-black text-slate-400">
                        支給量 上限日数 {g.max_service_days_type !== 'DYNAMIC_MONTH_MINUS_8' && <span className="text-rose-500 font-bold">*</span>}
                      </label>
                      <input
                        type="number"
                        disabled={g.max_service_days_type === 'DYNAMIC_MONTH_MINUS_8'}
                        required={g.max_service_days_type !== 'DYNAMIC_MONTH_MINUS_8'}
                        value={g.max_service_days_type === 'DYNAMIC_MONTH_MINUS_8' ? '' : (g.max_service_days ?? '')}
                        onChange={e => updateGrantedService(idx, 'max_service_days', e.target.value ? Number(e.target.value) : undefined)}
                        placeholder={g.max_service_days_type === 'DYNAMIC_MONTH_MINUS_8' ? '（自動計算）' : '例: 20'}
                        className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold disabled:bg-slate-100 disabled:text-slate-400"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-black text-slate-400">有効期間 開始〜終了</label>
                      <div className="flex items-center gap-1.5">
                        <input
                          type="date"
                          value={g.granted_amount_start_date || ''}
                          onChange={e => updateGrantedService(idx, 'granted_amount_start_date', e.target.value)}
                          className="w-1/2 bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                        />
                        <span className="text-slate-400">〜</span>
                        <input
                          type="date"
                          value={g.granted_amount_end_date || ''}
                          onChange={e => updateGrantedService(idx, 'granted_amount_end_date', e.target.value)}
                          className="w-1/2 bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                        />
                      </div>
                    </div>
                  </div>

                  {/* 契約内容報告（在籍情報・契約書）の入力フォーム（必須表示） */}
                  <div className="w-full mt-2 pt-2 border-t border-slate-100">
                    <div className="text-[10px] font-black text-indigo-900 mb-2">📄 契約内容報告（在籍情報・契約書）</div>
                    {g.contract_detail && (
                      <div className="w-full grid grid-cols-1 sm:grid-cols-3 gap-3 bg-indigo-50/20 p-3 rounded-xl border border-indigo-100/50 font-bold">
                        <div className="space-y-1">
                          <label className="text-[10px] font-black text-slate-400">契約事業所サービス <span className="text-rose-500 font-bold">*</span></label>
                          <select
                            required
                            value={g.contract_detail.office_service_configuration_id || ''}
                            onChange={e => {
                              const detail = { ...g.contract_detail, office_service_configuration_id: Number(e.target.value) };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                          >
                            <option value="">選択してください</option>
                            {officeSettings?.services?.map((s: any) => {
                              const sName = masters?.service_types.find(st => st.id === s.service_type_master_id)?.service_name || `ID:${s.service_type_master_id}`;
                              return <option key={s.id} value={s.id}>{officeSettings.office_name} - {sName}</option>;
                            })}
                          </select>
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-black text-slate-400">契約日 <span className="text-rose-500 font-bold">*</span></label>
                          <input
                            type="date"
                            required
                            value={g.contract_detail.contract_date || ''}
                            onChange={e => {
                              const detail = { ...g.contract_detail, contract_date: e.target.value };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-black text-slate-400">契約終了日 (任意)</label>
                          <input
                            type="date"
                            value={g.contract_detail.contract_end_date || ''}
                            onChange={e => {
                              const detail = { ...g.contract_detail, contract_end_date: e.target.value };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-black text-slate-400">契約終了月既提供日数 (任意)</label>
                          <input
                            type="number"
                            value={g.contract_detail.contract_end_used_days || 0}
                            onChange={e => {
                              const detail = { ...g.contract_detail, contract_end_used_days: e.target.value ? Number(e.target.value) : 0 };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-black text-slate-400">契約支給量 (原則の日数) <span className="text-rose-500 font-bold">*</span></label>
                          <input
                            type="number"
                            required
                            value={g.contract_detail.contract_granted_days || 23}
                            onChange={e => {
                              const detail = { ...g.contract_detail, contract_granted_days: e.target.value ? Number(e.target.value) : 23 };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                          />
                        </div>
                        <div className="space-y-1">
                          <label className="text-[10px] font-black text-slate-400">契約書 URL</label>
                          <input
                            type="text"
                            value={g.contract_detail.contract_document_url || ''}
                            onChange={e => {
                              const detail = { ...g.contract_detail, contract_document_url: e.target.value };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                            placeholder="https://..."
                          />
                        </div>
                        <div className="space-y-1 col-span-1 sm:col-span-3">
                          <label className="text-[10px] font-black text-slate-400">重要事項説明書 URL</label>
                          <input
                            type="text"
                            value={g.contract_detail.important_matters_url || ''}
                            onChange={e => {
                              const detail = { ...g.contract_detail, important_matters_url: e.target.value };
                              updateGrantedService(idx, 'contract_detail', detail);
                            }}
                            className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                            placeholder="https://..."
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {formData.granted_services.length === 0 && (
                <div className="text-center text-[10px] font-bold text-slate-400 py-2 border border-dashed border-slate-200 rounded-xl">
                  支給決定サービスが追加されていません
                </div>
              )}
            </div>
          </div>

          {/* 利用者負担上限額（必須入力・追加削除なし） */}
          <div className="pt-4 border-t border-indigo-100 font-bold">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-black text-slate-700">利用者負担上限額の設定</h4>
            </div>
            <div className="space-y-3">
              {(formData.copayment_limits || []).map((cl, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-xl p-3 space-y-3">
                  <div className="flex flex-wrap sm:flex-nowrap gap-3 items-end">
                    <div className="w-full sm:w-1/4 space-y-1">
                      <label className="text-[10px] font-black text-slate-400">上限負担額</label>
                      <select
                        value={cl.limit_amount}
                        onChange={e => updateCopaymentLimit(idx, 'limit_amount', Number(e.target.value))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      >
                        <option value={0}>0円 (一般・低所得)</option>
                        <option value={9300}>9,300円 (一般1)</option>
                        <option value={37200}>37,200円 (一般2)</option>
                      </select>
                    </div>
                    <div className="w-full sm:w-1/4 space-y-1">
                      <label className="text-[10px] font-black text-slate-400">適用開始日 <span className="text-rose-500 font-bold">*</span></label>
                      <input
                        type="date"
                        required
                        value={cl.limit_start_date}
                        onChange={e => updateCopaymentLimit(idx, 'limit_start_date', e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      />
                    </div>
                    <div className="w-full sm:w-1/4 space-y-1">
                      <label className="text-[10px] font-black text-slate-400">適用終了日 <span className="text-rose-500 font-bold">*</span></label>
                      <input
                        type="date"
                        required
                        value={cl.limit_end_date}
                        onChange={e => updateCopaymentLimit(idx, 'limit_end_date', e.target.value)}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                      />
                    </div>
                    <div className="w-full sm:w-1/4 pb-[6px]">
                      <label className="flex items-center gap-2 text-xs font-bold text-slate-600 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={cl.is_management_required}
                          onChange={e => updateCopaymentLimit(idx, 'is_management_required', e.target.checked)}
                          className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        上限管理あり
                      </label>
                    </div>
                  </div>

                  {cl.is_management_required && formData.copayment_managements?.[idx] && (
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-100">
                      <div className="space-y-1">
                        <label className="text-[10px] font-black text-slate-400">管理事業所番号 <span className="text-rose-500 font-bold">*</span></label>
                        <input
                          type="text"
                          required
                          value={formData.copayment_managements[idx].managing_office_number || ''}
                          onChange={e => {
                            const cmg = [...(formData.copayment_managements || [])];
                            cmg[idx] = { ...cmg[idx], managing_office_number: e.target.value };
                            setFormData({ ...formData, copayment_managements: cmg });
                          }}
                          placeholder="10桁の番号"
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-black text-slate-400">管理事業所名 <span className="text-rose-500 font-bold">*</span></label>
                        <input
                          type="text"
                          required
                          value={formData.copayment_managements[idx].managing_office_name || ''}
                          onChange={e => {
                            const cmg = [...(formData.copayment_managements || [])];
                            cmg[idx] = { ...cmg[idx], managing_office_name: e.target.value };
                            setFormData({ ...formData, copayment_managements: cmg });
                          }}
                          placeholder="事業所名"
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-black text-slate-400">管理開始日 <span className="text-rose-500 font-bold">*</span></label>
                        <input
                          type="date"
                          required
                          value={formData.copayment_managements[idx].management_start_date || ''}
                          onChange={e => {
                            const cmg = [...(formData.copayment_managements || [])];
                            cmg[idx] = { ...cmg[idx], management_start_date: e.target.value };
                            setFormData({ ...formData, copayment_managements: cmg });
                          }}
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                        />
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] font-black text-slate-400">管理終了日 <span className="text-rose-500 font-bold">*</span></label>
                        <input
                          type="date"
                          required
                          value={formData.copayment_managements[idx].management_end_date || ''}
                          onChange={e => {
                            const cmg = [...(formData.copayment_managements || [])];
                            cmg[idx] = { ...cmg[idx], management_end_date: e.target.value };
                            setFormData({ ...formData, copayment_managements: cmg });
                          }}
                          className="w-full bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-bold"
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {(formData.copayment_limits || []).length === 0 && (
                <div className="text-center text-[10px] font-bold text-slate-400 py-2 border border-dashed border-slate-200 rounded-xl">
                  負担上限額が設定されていません
                </div>
              )}
            </div>
          </div>

          {/* 食事提供加算 */}
          <div className="pt-4 border-t border-indigo-100">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-black text-slate-700">食事提供加算</h4>
              <button type="button" onClick={addMealAddonStatus} className="text-[10px] font-bold text-indigo-600 bg-indigo-100 hover:bg-indigo-200 px-2 py-1 rounded-lg flex items-center gap-1 transition-colors">
                <Plus size={12} /> 追加
              </button>
            </div>
            <div className="space-y-3">
              {(formData.meal_addon_statuses || []).map((ma, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-xl p-3 flex flex-wrap sm:flex-nowrap gap-3 items-end">
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">食事提供加算対象</label>
                    <select
                      value={ma.is_applicable ? 'true' : 'false'}
                      onChange={e => updateMealAddonStatus(idx, 'is_applicable', e.target.value === 'true')}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                    >
                      <option value="true">該当</option>
                      <option value="false">非該当</option>
                    </select>
                  </div>
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">適用開始日</label>
                    <input
                      type="date"
                      value={ma.meal_addon_start_date}
                      onChange={e => updateMealAddonStatus(idx, 'meal_addon_start_date', e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                    />
                  </div>
                  <div className="w-full sm:w-1/4 space-y-1">
                    <label className="text-[10px] font-black text-slate-400">適用終了日</label>
                    <input
                      type="date"
                      value={ma.meal_addon_end_date}
                      onChange={e => updateMealAddonStatus(idx, 'meal_addon_end_date', e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs font-bold"
                    />
                  </div>
                  <button type="button" onClick={() => removeMealAddonStatus(idx)} className="h-[28px] w-[28px] shrink-0 flex items-center justify-center text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg mb-[2px]">
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {(formData.meal_addon_statuses || []).length === 0 && (
                <div className="text-center text-[10px] font-bold text-slate-400 py-2 border border-dashed border-slate-200 rounded-xl">
                  食事提供加算の期間が設定されていません
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-indigo-100">
            {certificates.length > 0 && (
              <button
                type="button"
                onClick={handleCancel}
                className="bg-white hover:bg-slate-50 text-slate-600 font-bold px-6 py-2.5 rounded-xl border border-slate-200 transition-colors text-sm shadow-sm"
              >
                キャンセル
              </button>
            )}
            <button
              onClick={() => handleSaveClick('DRAFT')}
              disabled={isSubmitting}
              className="bg-slate-600 hover:bg-slate-700 text-white text-sm font-black px-6 py-2.5 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 shadow-md"
            >
              {isSubmitting ? '保存中...' : <><Save size={16} /> 下書き保存</>}
            </button>
            <button
              onClick={() => handleSaveClick('PENDING_REVIEW')}
              disabled={isSubmitting}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-black px-6 py-2.5 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 shadow-md"
            >
              {isSubmitting ? '提出中...' : <><Save size={16} /> 確認申請して保存</>}
            </button>
          </div>
        </div>
      )}

      {/* --- 履歴カード一覧 --- */}
      {!isFormVisible && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={handleNew} className="text-xs font-black text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-xl flex items-center gap-2 transition-colors">
              <Plus size={14} /> まったく新しい受給者証を登録
            </button>
          </div>
          
          {certificates.length === 0 ? (
            <div className="text-center py-8 text-slate-400 text-xs font-bold">受給者証の記録がありません</div>
          ) : (
            certificates.map((cert, index) => {
              const isLatest = index === 0;
              const municipality = masters?.municipalities.find(m => m.id === cert.municipality_master_id)?.city_name || `ID:${cert.municipality_master_id}`;
              
              return (
                <div key={cert.id} className={`border rounded-2xl p-4 transition-all ${isLatest ? 'border-indigo-200 bg-indigo-50/20 shadow-sm' : 'border-slate-200 bg-slate-50/50 opacity-75'}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {isLatest && <span className="bg-indigo-500 text-white text-[9px] font-black px-2 py-0.5 rounded-full">最新の受給者証</span>}
                        {cert.status && getStatusBadge(cert.status)}
                        <h4 className="text-sm font-black text-slate-800 flex items-center gap-1.5">
                          <Calendar size={14} className="text-slate-400" />
                          交付日: {cert.certificate_issue_date || '未設定'}
                        </h4>
                      </div>
                      <p className="text-xs font-bold text-slate-500">
                        {municipality} / {cert.certificate_type} {cert.disability_support_classification && `/ ${cert.disability_support_classification}`}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {/* 修正ボタン (DRAFT/REJECTED/ステータス未設定のみ表示) */}
                      {(!cert.status || cert.status === 'DRAFT' || cert.status === 'REJECTED') && (
                        <button 
                          onClick={() => handleEdit(cert)}
                          className="text-xs font-black text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 px-3 py-2 rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
                        >
                          <Edit3 size={14} className="text-slate-500" /> 修正
                        </button>
                      )}
                      
                      {/* 確認申請ボタン (DRAFT/REJECTEDのみ表示) */}
                      {(cert.status === 'DRAFT' || cert.status === 'REJECTED') && (
                        <button 
                          onClick={() => handleSubmitReview(cert.id)}
                          disabled={isSubmitting}
                          className="text-xs font-black text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-3 py-2 rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
                        >
                          確認申請
                        </button>
                      )}

                      {/* コピー変更ボタン (ACTIVE/ステータス未設定のみ表示) */}
                      {(!cert.status || cert.status === 'ACTIVE') && (
                        <button 
                          onClick={() => handleCopy(cert)}
                          className="text-xs font-black text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 px-3 py-2 rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
                        >
                          <Copy size={14} className="text-indigo-500" /> コピーして更新
                        </button>
                      )}

                      {/* 無効化ボタン (管理者かつACTIVE/PENDING_REVIEWのみ表示) */}
                      {isAdmin && (cert.status === 'ACTIVE' || cert.status === 'PENDING_REVIEW') && (
                        <button 
                          onClick={() => handleVoidClick(cert.id)}
                          disabled={isSubmitting}
                          className="text-xs font-black text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 disabled:opacity-50 px-3 py-2 rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
                        >
                          無効化
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 受給者証番号・管理サービス */}
                  <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-bold text-slate-600 bg-slate-50/50 p-3 rounded-xl border border-slate-100">
                    <div>
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">受給者証番号</span>
                      <p className="text-slate-800 font-black">{cert.recipient_number || '未設定'}</p>
                    </div>
                    <div>
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block mb-1">管理事業所サービス</span>
                      <p className="text-slate-800 font-black">
                        {(() => {
                          const config = officeSettings?.services?.find((s: any) => s.id === cert.office_service_configuration_id);
                          if (config) {
                            const sName = masters?.service_types.find(st => st.id === config.service_type_master_id)?.service_name || `ID:${config.service_type_master_id}`;
                            return `${officeSettings.office_name} - ${sName}`;
                          }
                          return '未設定';
                        })()}
                      </p>
                    </div>
                  </div>
                  
                  {cert.granted_services && cert.granted_services.length > 0 && (
                    <div className="mt-3 bg-white rounded-xl border border-slate-200 overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-[10px] font-black text-slate-500 uppercase tracking-wider">
                          <tr>
                            <th className="px-3 py-2">サービス</th>
                            <th className="px-3 py-2">支給決定期間</th>
                            <th className="px-3 py-2">支給量・日数</th>
                            <th className="px-3 py-2">契約・在籍情報</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-bold text-slate-700">
                          {cert.granted_services.map((g: any) => {
                            const serviceName = masters?.service_types.find(s => s.id === g.service_type_master_id)?.service_name || `ID:${g.service_type_master_id}`;
                            return (
                              <tr key={g.id}>
                                <td className="px-3 py-2 align-top font-black">{serviceName}</td>
                                <td className="px-3 py-2 align-top text-slate-500">
                                  <div>決定: {g.granted_start_date} 〜 {g.granted_end_date}</div>
                                  {(g.granted_amount_start_date || g.granted_amount_end_date) && (
                                    <div className="text-[10px] text-indigo-500 font-bold">
                                      有効期間: {g.granted_amount_start_date || ''} 〜 {g.granted_amount_end_date || ''}
                                    </div>
                                  )}
                                </td>
                                <td className="px-3 py-2 align-top">
                                  <div>{g.granted_amount_description || '未設定'}</div>
                                  <div className="text-[10px] text-slate-500 mt-0.5 font-bold">
                                    方式: {g.max_service_days_type === 'DYNAMIC_MONTH_MINUS_8' ? '該当月日数－8日' : `原則 ${g.max_service_days || 0} 日`}
                                  </div>
                                </td>
                                <td className="px-3 py-2 align-top">
                                  {g.contract_detail ? (
                                    <div className="space-y-0.5 text-[11px]">
                                      <div className="font-black text-slate-800">{g.contract_detail.contract_office_name || '在籍事業所不明'}</div>
                                      <div className="text-slate-500 text-[10px] font-bold">
                                        契約: {g.contract_detail.contract_date || '未登録'}
                                        {g.contract_detail.contract_end_date && ` 〜 ${g.contract_detail.contract_end_date}`}
                                      </div>
                                      {g.contract_detail.contract_end_used_days !== null && (
                                        <div className="text-slate-400 text-[9px] font-bold">
                                          終了月既提供日数: {g.contract_detail.contract_end_used_days}日
                                        </div>
                                      )}
                                      {(g.contract_detail.contract_document_url || g.contract_detail.important_matters_url) && (
                                        <div className="flex gap-2 mt-1">
                                          {g.contract_detail.contract_document_url && (
                                            <a href={g.contract_detail.contract_document_url} target="_blank" rel="noopener noreferrer" className="text-[9px] text-indigo-600 underline font-bold">契約書</a>
                                          )}
                                          {g.contract_detail.important_matters_url && (
                                            <a href={g.contract_detail.important_matters_url} target="_blank" rel="noopener noreferrer" className="text-[9px] text-indigo-600 underline font-bold">重説</a>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-slate-400 text-[10px]">未契約 / 未在籍</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* 負担上限額履歴 */}
                  {cert.copayment_limits && cert.copayment_limits.length > 0 && (
                    <div className="mt-3 bg-white rounded-xl border border-slate-200 overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-[10px] font-black text-slate-500 uppercase tracking-wider">
                          <tr>
                            <th className="px-3 py-2">適用期間 (負担上限額)</th>
                            <th className="px-3 py-2">上限負担額</th>
                            <th className="px-3 py-2">上限管理有無・管理先</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-bold text-slate-700">
                          {cert.copayment_limits.map((cl: any, idx: number) => {
                            const cmg = cert.copayment_managements?.[idx];
                            return (
                              <tr key={cl.id || idx}>
                                <td className="px-3 py-2 text-slate-500">{cl.limit_start_date} 〜 {cl.limit_end_date}</td>
                                <td className="px-3 py-2 text-indigo-600 font-black">{cl.limit_amount?.toLocaleString()} 円</td>
                                <td className="px-3 py-2">
                                  {cl.is_management_required ? (
                                    <div className="text-[11px] text-slate-800">
                                      <div className="font-black">あり: {cmg?.managing_office_name || '管理先不明'}</div>
                                      {cmg?.managing_office_number && (
                                        <div className="text-[9px] text-slate-400">事業所番号: {cmg.managing_office_number}</div>
                                      )}
                                      {cmg?.management_start_date && (
                                        <div className="text-[9px] text-slate-400">期間: {cmg.management_start_date} 〜 {cmg.management_end_date}</div>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-slate-400">管理不要</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* 食事提供加算履歴 */}
                  {cert.meal_addon_statuses && cert.meal_addon_statuses.length > 0 && (
                    <div className="mt-3 bg-white rounded-xl border border-slate-200 overflow-hidden">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 text-[10px] font-black text-slate-500 uppercase tracking-wider">
                          <tr>
                            <th className="px-3 py-2">適用期間 (食事提供加算)</th>
                            <th className="px-3 py-2">食事提供加算判定</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-bold text-slate-700">
                          {cert.meal_addon_statuses.map((ma: any, idx: number) => (
                            <tr key={ma.id || idx}>
                              <td className="px-3 py-2 text-slate-500">{ma.meal_addon_start_date} 〜 {ma.meal_addon_end_date}</td>
                              <td className="px-3 py-2">
                                <span className={ma.is_applicable ? 'text-indigo-600 font-black' : 'text-slate-400'}>
                                  {ma.is_applicable ? '該当' : '非該当'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {cert.certificate_notes && (
                    <div className="mt-3 text-xs font-bold text-slate-500 bg-slate-100/50 p-2 rounded-lg border border-slate-200/50">
                      備考: {cert.certificate_notes}
                    </div>
                  )}

                  {cert.review_reason && (
                    <div className={`mt-3 text-xs font-bold p-3 rounded-xl border ${cert.status === 'REJECTED' ? 'border-rose-200 bg-rose-50 text-rose-800' : 'border-slate-200 bg-slate-100/50 text-slate-600'}`}>
                      <span className="font-black block mb-0.5">{cert.status === 'REJECTED' ? '❌ 却下理由' : '📝 確認コメント'}</span>
                      {cert.review_reason}
                    </div>
                  )}

                  {cert.status === 'VOIDED' && cert.void_reason && (
                    <div className="mt-3 text-xs font-bold p-3 rounded-xl border border-red-200 bg-red-50 text-red-800 animate-in fade-in duration-200">
                      <span className="font-black block mb-0.5">❌ 無効化理由</span>
                      {cert.void_reason}
                    </div>
                  )}

                  {/* 確認・承認用パネル (PENDING_REVIEW の場合のみ表示) */}
                  {cert.status === 'PENDING_REVIEW' && (
                    <div className="mt-4 p-4 rounded-xl border border-amber-200 bg-amber-50/50 space-y-3 font-bold text-xs">
                      <div className="text-amber-900 font-black flex items-center gap-1.5">
                        <AlertCircle size={16} className="text-amber-600" />
                        <span>受給者証情報の承認確認</span>
                      </div>
                      
                      {cert.submitted_by_supporter_id === currentUser?.id ? (
                        <p className="text-slate-500 italic">
                          ※自身が申請した受給者証の確認・承認は行えません。他の職員による確認をお待ちください。
                        </p>
                      ) : (
                        <div className="space-y-2.5">
                          {reviewErrors[cert.id] && (
                            <div className="text-rose-600 text-[10px] font-black">
                              ⚠️ {reviewErrors[cert.id]}
                            </div>
                          )}
                          <div className="space-y-1">
                            <span className="text-[10px] font-black text-slate-500 block">確認コメント（却下時は入力必須）</span>
                            <input
                              type="text"
                              value={reviewComments[cert.id] || ''}
                              onChange={e => setReviewComments(prev => ({ ...prev, [cert.id]: e.target.value }))}
                              placeholder="確認事項や却下理由を入力してください"
                              className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-bold"
                            />
                          </div>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => handleReviewAction(cert.id, 'approve')}
                              disabled={isSubmitting}
                              className="bg-emerald-600 hover:bg-emerald-700 text-white font-black px-4 py-1.5 rounded-lg transition-colors"
                            >
                              承認する
                            </button>
                            <button
                              type="button"
                              onClick={() => handleReviewAction(cert.id, 'reject')}
                              disabled={isSubmitting}
                              className="bg-rose-600 hover:bg-rose-700 text-white font-black px-4 py-1.5 rounded-lg transition-colors"
                            >
                              却下する
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* 更新理由入力モーダル */}
      {isReasonModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-100 space-y-4 animate-in zoom-in-95 duration-200">
            <h3 className="text-sm font-black text-slate-900 flex items-center gap-2">
              <Edit3 size={18} className="text-indigo-500" />
              受給者証情報の更新理由
            </h3>
            <p className="text-xs font-bold text-slate-500 leading-relaxed">
              監査証跡（Audit Log）として記録するため、受給者証情報を変更する「理由（原因）」を入力してください。
            </p>
            {reasonError && (
              <div className="bg-rose-50 text-rose-600 p-2 rounded-xl text-[10px] font-black flex items-center gap-2">
                <AlertCircle size={14} />
                {reasonError}
              </div>
            )}
            <div className="space-y-1">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">更新理由 (任意)</label>
              <textarea
                value={updateReasonText}
                onChange={e => {
                  setUpdateReasonText(e.target.value);
                }}
                placeholder="例: 受給者証の更新に伴う修正"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold h-24 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setIsReasonModalOpen(false);
                  setUpdateReasonText('');
                  setReasonError(null);
                }}
                className="bg-white hover:bg-slate-50 text-slate-600 font-bold px-4 py-2 rounded-xl border border-slate-200 transition-colors text-xs shadow-sm"
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleReasonSubmit}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-black px-6 py-2 rounded-xl flex items-center gap-2 transition-all shadow-md"
              >
                理由を送信して保存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 無効化理由入力モーダル */}
      {isVoidModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl border border-slate-100 space-y-4 animate-in zoom-in-95 duration-200">
            <h3 className="text-sm font-black text-rose-600 flex items-center gap-2">
              <AlertCircle size={18} className="text-rose-500" />
              受給者証情報の無効化
            </h3>
            <p className="text-xs font-bold text-slate-500 leading-relaxed">
              誤登録の無効化処理を行います。監査証跡として記録するため、無効化する「理由」（必須）を入力してください。
            </p>
            {voidError && (
              <div className="bg-rose-50 text-rose-600 p-2 rounded-xl text-[10px] font-black flex items-center gap-2">
                <AlertCircle size={14} />
                {voidError}
              </div>
            )}
            <div className="space-y-1">
              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">無効化理由 (必須)</label>
              <textarea
                value={voidReasonText}
                onChange={e => {
                  setVoidReasonText(e.target.value);
                }}
                placeholder="例: 有効期間の入力を誤って確定してしまったため無効化し、再登録します。"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold h-24 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              />
            </div>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  setIsVoidModalOpen(false);
                  setVoidReasonText('');
                  setVoidTargetCertId(null);
                  setVoidError(null);
                }}
                className="bg-white hover:bg-slate-50 text-slate-600 font-bold px-4 py-2 rounded-xl border border-slate-200 transition-colors text-xs shadow-sm"
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleVoidSubmit}
                disabled={isSubmitting}
                className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-black px-6 py-2 rounded-xl flex items-center gap-2 transition-all shadow-md disabled:opacity-50"
              >
                無効化を実行
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

