// frontend/src/services/userService.ts

import apiClient from './apiClient';

export interface UserListItem {
  id: number;
  display_name: string;
  status_id?: number;
  status_name?: string;
  service_start_date?: string | null;
  has_certificate_number?: boolean;
  active_plan_end_date?: string | null;
}

// APIから返ってくるデータの型定義
export interface UserPiiResponse {
  id: number;
  display_name: string;
  status_id?: number;
  status_name?: string;
  service_start_date?: string | null;
  service_end_date?: string | null;
  support_plan: {
    id: number;
    status: string;
    start_date: string | null;
    end_date: string | null;
  } | null;
  emergency_contacts: {
    id: number;
    name: string;
    phone_number: string;
    relation: string;
  }[];
  profile?: {
    emergency_contact_notes?: string;
    insurance_details?: string;
  };
  pii: {
    last_name: string;
    first_name: string;
    last_name_kana: string;
    first_name_kana: string;
    address: string;
    phone_number: string;
    email: string;
    birth_date: string | null;
    certificate_number?: string | null;
  };
  certificates?: {
    id: number;
    certificate_issue_date: string | null;
    municipality_master_id: number;
    certificate_type: string | null;
    disability_support_classification: string | null;
    certificate_notes: string | null;
    recipient_number: string | null;
    granted_services: {
      id: number;
      service_type_master_id: number;
      granted_start_date: string | null;
      granted_end_date: string | null;
      granted_amount_description: string | null;
      max_service_days: number | null;
      max_service_days_type: string;
      granted_amount_start_date: string | null;
      granted_amount_end_date: string | null;
      contract_detail: {
        office_service_configuration_id: number;
        contract_office_name: string | null;
        contract_corporation_name: string | null;
        contract_service_type: string | null;
        contract_date: string | null;
        contract_end_date: string | null;
        contract_end_used_days: number | null;
        contract_granted_days: number | null;
        contract_document_url?: string | null;
        important_matters_url?: string | null;
      } | null;
    }[];
    copayment_limits: {
      id: number;
      limit_start_date: string | null;
      limit_end_date: string | null;
      limit_amount: number;
      is_management_required: boolean;
    }[];
    meal_addon_statuses: {
      id: number;
      meal_addon_start_date: string | null;
      meal_addon_end_date: string | null;
      is_applicable: boolean;
    }[];
    copayment_managements: {
      id: number;
      management_start_date: string | null;
      management_end_date: string | null;
      is_applicable: boolean;
      managing_office_number: string | null;
      managing_office_name: string | null;
    }[];
    status?: string;
    created_by_supporter_id?: number | null;
    submitted_by_supporter_id?: number | null;
    reviewed_by_supporter_id?: number | null;
    reviewed_at?: string | null;
    review_reason?: string | null;
    voided_by_supporter_id?: number | null;
    voided_at?: string | null;
    void_reason?: string | null;
  }[];
}

export interface StatusMaster {
  id: number;
  name: string;
  description: string;
}

/**
 * 利用者一覧を取得する
 */
export const fetchUserList = async (statusIds?: number[]): Promise<UserListItem[]> => {
  const params = statusIds && statusIds.length > 0 ? { status_ids: statusIds.join(',') } : {};
  const response = await apiClient.get<UserListItem[]>('/users', { params });
  return response.data;
};

export const fetchStatusMaster = async (): Promise<StatusMaster[]> => {
  const response = await apiClient.get<StatusMaster[]>('/users/statuses');
  return response.data;
};

export interface UpdateUserStatusData {
  status_id: number;
  service_start_date?: string | null;
  service_end_date?: string | null;
}

export const updateUserStatus = async (userId: number, data: UpdateUserStatusData): Promise<{ msg: string }> => {
  const response = await apiClient.put<{ msg: string }>(`/users/${userId}/status`, data);
  return response.data;
};

/**
 * 指定した利用者のPIIを取得する
 * (VIEW_PII 権限が必要)
 */
export const fetchUserPii = async (userId: number): Promise<UserPiiResponse> => {
  const response = await apiClient.get<UserPiiResponse>(`/users/${userId}/pii`);
  return response.data;
};

/**
 * 特定のPII情報を復号化して取得する
 */
export const decryptUserPii = async (userId: number, piiType: 'phone' | 'email' | 'address' | 'name' | 'certificate_number'): Promise<{ val: string }> => {
  const response = await apiClient.post<{ val: string }>(`/users/${userId}/decrypt-pii`, { pii_type: piiType });
  return response.data;
};

export interface UpdateUserData {
  display_name?: string;
  pii?: {
    last_name?: string;
    first_name?: string;
    last_name_kana?: string;
    first_name_kana?: string;
    address?: string;
    phone_number?: string;
    email?: string;
    birth_date?: string | null;
    certificate_number?: string | null;
  };
  profile?: {
    emergency_contact_notes?: string;
    insurance_details?: string;
  };
  emergency_contacts?: {
    name: string;
    phone_number: string;
    relation: string;
  }[];
}

/**
 * 利用者情報を更新する
 */
export const updateUserDetails = async (userId: number, data: UpdateUserData): Promise<void> => {
  await apiClient.put(`/users/${userId}`, data);
};

export interface CreateUserData {
  display_name: string;
  pii?: {
    last_name?: string;
    first_name?: string;
    last_name_kana?: string;
    first_name_kana?: string;
    address?: string;
    phone_number?: string;
    email?: string;
    birth_date?: string | null;
    certificate_number?: string | null;
  };
  profile?: {
    emergency_contact_notes?: string;
    insurance_details?: string;
  };
  emergency_contacts?: {
    name: string;
    phone_number: string;
    relation: string;
  }[];
}

/**
 * 利用者を新規追加する
 */
export const registerUser = async (data: CreateUserData): Promise<{user_id: number, user_code: string}> => {
  const response = await apiClient.post<{user_id: number, user_code: string}>('/users', data);
  return response.data;
};

/**
 * 下書きを一時保存（オートセーブ）する
 */
export const saveDraft = async (draftKey: string, data: Record<string, unknown>): Promise<void> => {
  await apiClient.post('/users/drafts', { draft_key: draftKey, data });
};

/**
 * 下書きを読み込む
 */
export const loadDraft = async (draftKey: string): Promise<Record<string, unknown> | null> => {
  const response = await apiClient.get<{ data: Record<string, unknown> | null }>(`/users/drafts/${draftKey}`);
  return response.data.data;
};

/**
 * 下書きを消去する
 */
export const clearDraft = async (draftKey: string): Promise<void> => {
  await apiClient.delete(`/users/drafts/${draftKey}`);
};

export interface ServiceCertificateData {
  certificate_issue_date: string;
  municipality_master_id: number;
  certificate_type: string;
  disability_support_classification: string;
  recipient_number?: string | null;
  certificate_notes?: string;
  office_service_configuration_id?: number | null;
  update_reason?: string;
  granted_services: {
    service_type_master_id: number;
    granted_start_date: string;
    granted_end_date: string;
    granted_amount_description: string;
    max_service_days: number | null;
    max_service_days_type: string;
    granted_amount_start_date: string | null;
    granted_amount_end_date: string | null;
    contract_detail: {
      office_service_configuration_id: number;
      contract_date: string | null;
      contract_end_date: string | null;
      contract_end_used_days: number | null;
      contract_granted_days: number | null;
      contract_document_url?: string | null;
      important_matters_url?: string | null;
    } | null;
  }[];
  copayment_limits?: {
    limit_start_date: string;
    limit_end_date: string;
    limit_amount: number;
    is_management_required: boolean;
  }[];
  meal_addon_statuses?: {
    meal_addon_start_date: string;
    meal_addon_end_date: string;
    is_applicable: boolean;
  }[];
  copayment_managements?: {
    management_start_date: string;
    management_end_date: string;
    is_applicable: boolean;
    managing_office_number: string | null;
    managing_office_name: string | null;
  }[];
  status?: string;
  created_by_supporter_id?: number | null;
  submitted_by_supporter_id?: number | null;
  reviewed_by_supporter_id?: number | null;
  reviewed_at?: string | null;
  review_reason?: string | null;
  voided_by_supporter_id?: number | null;
  voided_at?: string | null;
  void_reason?: string | null;
}

export const addServiceCertificate = async (userId: number, data: ServiceCertificateData): Promise<{ msg: string, id: number }> => {
  const response = await apiClient.post<{ msg: string, id: number }>(`/users/${userId}/certificates`, data);
  return response.data;
};

export const updateServiceCertificate = async (userId: number, certId: number, data: ServiceCertificateData): Promise<{ msg: string, id: number }> => {
  const response = await apiClient.put<{ msg: string, id: number }>(`/users/${userId}/certificates/${certId}`, data);
  return response.data;
};

export const submitServiceCertificate = async (userId: number, certId: number): Promise<{ msg: string, status: string }> => {
  const response = await apiClient.post<{ msg: string, status: string }>(`/users/${userId}/certificates/${certId}/submit`);
  return response.data;
};

export const reviewServiceCertificate = async (userId: number, certId: number, action: 'approve' | 'reject', reviewReason?: string): Promise<{ msg: string, status: string }> => {
  const response = await apiClient.post<{ msg: string, status: string }>(`/users/${userId}/certificates/${certId}/review`, { action, review_reason: reviewReason });
  return response.data;
};

export const voidServiceCertificate = async (userId: number, certId: number, voidReason: string): Promise<{ msg: string, status: string }> => {
  const response = await apiClient.post<{ msg: string, status: string }>(`/users/${userId}/certificates/${certId}/void`, { void_reason: voidReason });
  return response.data;
};

// ============================================================
// UserDetailPage タブ用 API
// ============================================================

// --- 個別支援計画 ---
export interface IndividualGoal {
  id: number;
  concrete_goal: string;
  user_commitment: string;
  support_actions: string;
  service_type: string;
}
export interface ShortTermGoal {
  id: number;
  description: string;
  target_period_start: string | null;
  target_period_end: string | null;
  next_review_date: string | null;
  individual_goals: IndividualGoal[];
}
export interface LongTermGoal {
  id: number;
  description: string;
  challenges?: string | null;
  target_period_start: string | null;
  target_period_end: string | null;
  short_term_goals: ShortTermGoal[];
}
export interface HolisticPolicySummary {
  id: number;
  user_intention_content: string;
  support_policy_content: string;
}

export interface ActiveSupportPlan {
  id: number;
  plan_version: number;
  plan_status: string;
  start_date: string | null;
  end_date: string | null;
  next_monitoring_due: string | null;
  created_at: string | null;
  based_on_plan_id: number | null;
  holistic_policy: HolisticPolicySummary | null;
  long_term_goals: LongTermGoal[];
  draft_created_at?: string | null;
  explained_at?: string | null;
  consented_at?: string | null;
  activated_at?: string | null;
  timeline_deviation_reason?: string | null;
}
export interface SupportPlanSummary {
  id: number;
  plan_version: number;
  plan_status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string | null;
  based_on_plan_id: number | null;
  holistic_policy: HolisticPolicySummary | null;
  draft_created_at?: string | null;
  explained_at?: string | null;
  consented_at?: string | null;
  activated_at?: string | null;
  timeline_deviation_reason?: string | null;
  long_term_goals?: {
    description: string;
    challenges?: string | null;
    short_term_goals: {
      description: string;
    }[];
  }[];
}
export interface UserSupportPlansResponse {
  active_plan: ActiveSupportPlan | null;
  plan_history: SupportPlanSummary[];
}

export const fetchUserSupportPlans = async (userId: number): Promise<UserSupportPlansResponse> => {
  const response = await apiClient.get<UserSupportPlansResponse>(`/users/${userId}/support-plans`);
  return response.data;
};

export interface RecordConsentResponse {
  msg: string;
  consent_log_id: number;
}

export const recordUserConsent = async (planId: number, userId: number, consentProof: string, generatedDocumentUrl?: string): Promise<RecordConsentResponse> => {
  const response = await apiClient.post<RecordConsentResponse>(`/plans/${planId}/consent`, {
    user_id: userId,
    consent_proof: consentProof,
    generated_document_url: generatedDocumentUrl
  });
  return response.data;
};

export interface ActivatePlanResponse {
  msg: string;
  plan_id: number;
  status: string;
}

export const activateSupportPlan = async (planId: number, consentLogId: number): Promise<ActivatePlanResponse> => {
  const response = await apiClient.post<ActivatePlanResponse>(`/plans/${planId}/activate`, {
    consent_log_id: consentLogId
  });
  return response.data;
};

export interface CreateSupportPlanResponse {
  msg: string;
  plan_id: number;
  user_id: number;
  status: string;
}

export interface CreateSupportPlanParams {
  userId: number;
  holisticSupportPolicyId?: number;
  planStartDate?: string;
  planEndDate?: string;
  userIntentionContent?: string;
  supportPolicyContent?: string;
}

export const createSupportPlanDraft = async (params: CreateSupportPlanParams): Promise<CreateSupportPlanResponse> => {
  const response = await apiClient.post<CreateSupportPlanResponse>('/plans', {
    user_id: params.userId,
    holistic_support_policy_id: params.holisticSupportPolicyId,
    plan_start_date: params.planStartDate,
    plan_end_date: params.planEndDate,
    user_intention_content: params.userIntentionContent,
    support_policy_content: params.supportPolicyContent,
  });
  return response.data;
};

export interface CloneNextDraftResponse {
  msg: string;
  plan_id: number;
  status: string;
}

export const createNextSupportPlanDraft = async (planId: number): Promise<CloneNextDraftResponse> => {
  const response = await apiClient.post<CloneNextDraftResponse>(`/plans/${planId}/create-next-draft`);
  return response.data;
};

export interface SaveGoalsData {
  long_term_goals: {
    description: string;
    challenges: string;
    short_term_goals: {
      description: string;
      individual_goals: {
        concrete_goal: string;
        user_commitment: string;
        support_actions: string;
        service_type: string;
        is_facility_in_deemed: boolean;
        is_work_preparation_positioning: boolean;
      }[];
    }[];
  }[];
}

export const saveSupportPlanGoals = async (planId: number, data: SaveGoalsData): Promise<{ msg: string }> => {
  const response = await apiClient.put<{ msg: string }>(`/plans/${planId}/goals`, data);
  return response.data;
};

export interface DetailedSupportPlanResponse {
  id: number;
  plan_version: number;
  plan_status: string;
  start_date: string | null;
  end_date: string | null;
  based_on_plan_id: number | null;
  holistic_policy: {
    id: number;
    user_intention_content: string;
    support_policy_content: string;
  } | null;
  long_term_goals: {
    id: number;
    description: string;
    challenges?: string | null;
    short_term_goals: {
      id: number;
      description: string;
      individual_goals: {
        id: number;
        concrete_goal: string;
        user_commitment: string;
        support_actions: string;
        service_type: string;
        is_facility_in_deemed?: boolean;
        is_work_preparation_positioning?: boolean;
      }[];
    }[];
  }[];
}

export const getSupportPlanDetails = async (planId: number): Promise<DetailedSupportPlanResponse> => {
  const response = await apiClient.get<DetailedSupportPlanResponse>(`/plans/${planId}`);
  return response.data;
};

export const updateSupportPlanDraft = async (
  planId: number,
  params: {
    planStartDate?: string;
    planEndDate?: string;
    userIntentionContent?: string;
    supportPolicyContent?: string;
  }
): Promise<{ msg: string }> => {
  const response = await apiClient.put<{ msg: string }>(`/plans/${planId}`, {
    plan_start_date: params.planStartDate,
    plan_end_date: params.planEndDate,
    user_intention_content: params.userIntentionContent,
    support_policy_content: params.supportPolicyContent,
  });
  return response.data;
};

// --- 日報 ---
export interface DailyLogActivity {
  id: number;
  support_content: string;
  start_time: string | null;
  end_time: string | null;
  supporter_name: string;
  duration_seconds?: number;
}
export interface DailyLogItem {
  id: number;
  log_date: string;
  log_status: string;
  support_content_notes: string;
  location_type: string;
  activities: DailyLogActivity[];
}
export interface UserDailyLogsResponse {
  items: DailyLogItem[];
}

export const fetchUserDailyLogs = async (userId: number, limit = 20, offset = 0): Promise<UserDailyLogsResponse> => {
  const response = await apiClient.get<UserDailyLogsResponse>(`/users/${userId}/daily-logs`, {
    params: { limit, offset },
  });
  return response.data;
};

// --- モニタリング ---
export interface MonitoringHistoryItem {
  id: number;
  report_date: string;
  monitoring_summary: string;
  target_goal_progress_notes: string | null;
  support_plan_id: number;
  supporter_name: string;
}
export interface UserMonitoringResponse {
  next_monitoring_due: string | null;
  active_plan_summary: {
    id: number;
    plan_version: number;
    start_date: string | null;
    end_date: string | null;
    primary_goal: string | null;
  } | null;
  history: MonitoringHistoryItem[];
}

export const fetchUserMonitoringReports = async (userId: number): Promise<UserMonitoringResponse> => {
  const response = await apiClient.get<UserMonitoringResponse>(`/users/${userId}/monitoring-reports`);
  return response.data;
};

// --- ケース会議 ---
export interface CaseConferenceItem {
  id: number;
  conference_datetime: string | null;
  conference_type: string;
  concern_summary: string;
  agreed_action: string;
  plan_direction_update: string | null;
  external_collaboration_required: boolean;
  initiator_name: string;
  participants: string[];
  support_plan_id?: number | null;
  user_participated?: boolean;
  reason_for_user_absence?: string | null;
  is_sabikan_digital_declaration?: boolean;
  absence_monitoring_summary?: string | null;
  plan_goals?: {
    description: string;
    short_term_goals: string[];
  }[];
}
export interface UserCaseConferencesResponse {
  items: CaseConferenceItem[];
}

export const fetchUserCaseConferences = async (userId: number): Promise<UserCaseConferencesResponse> => {
  const response = await apiClient.get<UserCaseConferencesResponse>(`/users/${userId}/case-conferences`);
  return response.data;
};

export interface CreateCaseConferenceData {
  user_id: number;
  conference_type: string;
  concern_summary: string;
  agreed_action: string;
  participant_ids?: number[];
  conference_datetime?: string;
  support_plan_id?: number | null;
  user_participated?: boolean;
  reason_for_user_absence?: string;
  is_sabikan_digital_declaration?: boolean;
  absence_monitoring_summary?: string;
}

export const createCaseConference = async (data: CreateCaseConferenceData): Promise<{ msg: string, id: number }> => {
  const response = await apiClient.post<{ msg: string, id: number }>('/case-conferences', data);
  return response.data;
};

export interface SupporterOption {
  id: number;
  name: string;
}

export const fetchActiveSupporters = async (): Promise<SupporterOption[]> => {
  const response = await apiClient.get<SupporterOption[]>('/case-conferences/supporters');
  return response.data;
};

export interface CreateMonitoringData {
  support_plan_id: number;
  report_date: string;
  monitoring_summary: string;
  target_goal_progress_notes?: string;
  contextual_analysis?: string;
}

export const createMonitoringReport = async (data: CreateMonitoringData): Promise<{ msg: string, id: number }> => {
  const response = await apiClient.post<{ msg: string, id: number }>('/monitoring-reports', data);
  return response.data;
};

export const approveSupportPlan = async (planId: number): Promise<{ msg: string, plan_id: number }> => {
  const response = await apiClient.post<{ msg: string, plan_id: number }>(`/plans/${planId}/approve`);
  return response.data;
};

export const updateTimelineDeviationReason = async (planId: number, reason: string): Promise<{ msg: string }> => {
  const response = await apiClient.put<{ msg: string }>(`/plans/${planId}/deviation-reason`, { timeline_deviation_reason: reason });
  return response.data;
};

// --- 管理確認事項 (Action Items) ---
export interface ActionItem {
  type: 'daily_log' | 'monitoring' | 'approval' | 'case_conference' | 'support_plan_timeline' | 'unexcused_absence' | 'unscheduled_attendance' | 'support_record_missing' | 'schedule_request_pending';
  category_label: string;
  severity: 'high' | 'medium' | 'low';
  user_id: number;
  user_name: string;
  title: string;
  description: string;
  target_date?: string;
  attendance_record_id?: number;
  check_in_at?: string;
  check_out_at?: string;
}

export interface ActionItemsResponse {
  items: ActionItem[];
}

export const fetchActionItems = async (): Promise<ActionItemsResponse> => {
  const response = await apiClient.get<ActionItemsResponse>('/action-items');
  return response.data;
};

// --- 日報登録関連 ---
export interface ActivityTag {
  id: number;
  name: string;
  is_direct_support: boolean;
}

export interface CreateDailyLogData {
  tag_id: number;
  user_id: number;
  start_time: string;
  end_time: string;
  duration_seconds: number;
  notes: string;
  log_status: 'DRAFT' | 'COMPLETED';
  attendance_record_id?: number;
}

export const fetchActivityTags = async (): Promise<ActivityTag[]> => {
  const response = await apiClient.get<ActivityTag[]>('/daily-logs/tags');
  return response.data;
};

export const createDailyLog = async (data: CreateDailyLogData): Promise<{ msg: string }> => {
  const response = await apiClient.post<{ msg: string }>('/daily-logs', data);
  return response.data;
};

export interface UserAttendanceItem {
  attendance_record_id: number;
  date: string;
  check_in_at: string | null;
  check_out_at: string | null;
  status: 'IDLE' | 'CHECKED_IN' | 'CHECKED_OUT';
  daily_log_status: 'missing' | 'draft' | 'completed';
  scheduled_location_type?: string | null;
  actual_location_type?: string | null;
  scheduled_start_time?: string | null;
  scheduled_end_time?: string | null;
  is_scheduled?: boolean;
  schedule_status?: string | null;
  approval_status?: string | null;
}

export interface UserAttendanceResponse {
  items: UserAttendanceItem[];
}

export const fetchUserAttendanceRecords = async (userId: number): Promise<UserAttendanceResponse> => {
  const response = await apiClient.get<UserAttendanceResponse>(`/users/${userId}/attendance-records`);
  return response.data;
};

export interface TodayUserItem {
  user_id: number;
  user_name: string;
  attendance_record_id: number;
  check_in_at: string;
  check_out_at: string | null;
  status: 'CHECKED_IN' | 'CHECKED_OUT';
  daily_log_status: 'missing' | 'draft' | 'completed';
}

export interface TodayUsersResponse {
  items: TodayUserItem[];
}

export const fetchTodayUsers = async (): Promise<TodayUsersResponse> => {
  const response = await apiClient.get<TodayUsersResponse>('/dashboard/today-users');
  return response.data;
};

// --- 利用者予定・申請管理 ---
export interface UserScheduleTemplateItem {
  day_of_week: string;
  is_scheduled: boolean;
  start_time: string | null;
  end_time: string | null;
}

export interface UserScheduleRequestItem {
  id: number;
  target_date: string;
  request_type: 'ABSENCE' | 'EXTRA_DAY' | 'SHIFT_TIME';
  requested_start_time: string | null;
  requested_end_time: string | null;
  request_reason: string;
  request_status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  requested_by_user_id: number | null;
  requested_by_supporter_id: number | null;
  decided_by_supporter_id: number | null;
  decided_at: string | null;
  decision_reason: string | null;
}

export interface UserDailyScheduleItem {
  id: number;
  date: string;
  start_time: string | null;
  end_time: string | null;
  is_scheduled: boolean;
  schedule_status: 'NORMAL' | 'CANCELLED' | 'SUBSTITUTED' | 'EXTRA';
  approval_status?: 'APPROVED' | 'CANCELLED' | 'REQUESTED' | 'REJECTED';
  location_type?: string | null;
  schedule_request_id: number | null;
  decision_reason?: string | null;
  actual_check_in?: string | null;
  actual_check_out?: string | null;
}

export const fetchUserScheduleTemplates = async (userId: number): Promise<{ items: UserScheduleTemplateItem[] }> => {
  const response = await apiClient.get<{ items: UserScheduleTemplateItem[] }>(`/users/${userId}/schedule-templates`);
  return response.data;
};

export const saveUserScheduleTemplates = async (userId: number, data: UserScheduleTemplateItem[]): Promise<{ success: boolean, message: string }> => {
  const response = await apiClient.post<{ success: boolean, message: string }>(`/users/${userId}/schedule-templates`, data);
  return response.data;
};

export const fetchUserScheduleRequests = async (userId: number): Promise<{ items: UserScheduleRequestItem[] }> => {
  const response = await apiClient.get<{ items: UserScheduleRequestItem[] }>(`/users/${userId}/schedule-requests`);
  return response.data;
};

export const createUserScheduleRequest = async (
  userId: number,
  data: {
    target_date: string;
    request_type: 'ABSENCE' | 'EXTRA_DAY' | 'SHIFT_TIME';
    request_reason: string;
    requested_start_time?: string | null;
    requested_end_time?: string | null;
  }
): Promise<{ success: boolean, item: { id: number, request_status: string } }> => {
  const response = await apiClient.post<{ success: boolean, item: { id: number, request_status: string } }>(`/users/${userId}/schedule-requests`, data);
  return response.data;
};

export const fetchUserDailySchedules = async (
  userId: number,
  params?: { start_date?: string; end_date?: string }
): Promise<{ items: UserDailyScheduleItem[] }> => {
  const response = await apiClient.get<{ items: UserDailyScheduleItem[] }>(`/users/${userId}/daily-schedules`, { params });
  return response.data;
};

export const updateUserDailySchedule = async (
  userId: number,
  dateStr: string,
  data: {
    is_scheduled?: boolean;
    start_time?: string | null;
    end_time?: string | null;
    location_type?: string | null;
    decision_reason?: string | null;
  }
): Promise<{ success: boolean, item: UserDailyScheduleItem }> => {
  const response = await apiClient.put<{ success: boolean, item: UserDailyScheduleItem }>(`/users/${userId}/daily-schedules/${dateStr}`, data);
  return response.data;
};

export const decideUserScheduleRequest = async (
  requestId: number,
  data: { status: 'APPROVED' | 'REJECTED'; decision_reason: string }
): Promise<{ success: boolean, item: { id: number, request_status: string, decision_reason: string } }> => {
  const response = await apiClient.post<{ success: boolean, item: { id: number, request_status: string, decision_reason: string } }>(`/users/schedule-requests/${requestId}/decide`, data);
  return response.data;
};

// --- 日別予定・実績一覧 ---
export interface DailyScheduleActualItem {
  user_id: number;
  user_name: string;
  is_scheduled: boolean;
  scheduled_start_time: string | null;
  scheduled_end_time: string | null;
  schedule_status: string | null;
  check_in_at: string | null;
  check_out_at: string | null;
  effective_status: string;
  daily_log_status: 'missing' | 'draft' | 'completed';
}

export const fetchDailyScheduleActuals = async (date?: string): Promise<{ items: DailyScheduleActualItem[] }> => {
  const params = date ? { date } : {};
  const response = await apiClient.get<{ items: DailyScheduleActualItem[] }>('/schedules/daily-actuals', { params });
  return response.data;
};