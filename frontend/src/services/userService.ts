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
    granted_services: {
      id: number;
      service_type_master_id: number;
      granted_start_date: string | null;
      granted_end_date: string | null;
      granted_amount_description: string | null;
    }[];
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
  certificate_notes?: string;
  granted_services: {
    service_type_master_id: number;
    granted_start_date: string;
    granted_end_date: string;
    granted_amount_description: string;
  }[];
}

export const addServiceCertificate = async (userId: number, data: ServiceCertificateData): Promise<{ msg: string, id: number }> => {
  const response = await apiClient.post<{ msg: string, id: number }>(`/users/${userId}/certificates`, data);
  return response.data;
};

export const updateServiceCertificate = async (userId: number, certId: number, data: ServiceCertificateData): Promise<{ msg: string, id: number }> => {
  const response = await apiClient.put<{ msg: string, id: number }>(`/users/${userId}/certificates/${certId}`, data);
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
  target_period_start: string | null;
  target_period_end: string | null;
  short_term_goals: ShortTermGoal[];
}
export interface ActiveSupportPlan {
  id: number;
  plan_version: number;
  plan_status: string;
  start_date: string | null;
  end_date: string | null;
  next_monitoring_due: string | null;
  created_at: string | null;
  long_term_goals: LongTermGoal[];
}
export interface SupportPlanSummary {
  id: number;
  plan_version: number;
  plan_status: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string | null;
}
export interface UserSupportPlansResponse {
  active_plan: ActiveSupportPlan | null;
  plan_history: SupportPlanSummary[];
}

export const fetchUserSupportPlans = async (userId: number): Promise<UserSupportPlansResponse> => {
  const response = await apiClient.get<UserSupportPlansResponse>(`/users/${userId}/support-plans`);
  return response.data;
};

// --- 日報 ---
export interface DailyLogActivity {
  id: number;
  support_content: string;
  start_time: string | null;
  end_time: string | null;
  supporter_name: string;
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
}
export interface UserCaseConferencesResponse {
  items: CaseConferenceItem[];
}

export const fetchUserCaseConferences = async (userId: number): Promise<UserCaseConferencesResponse> => {
  const response = await apiClient.get<UserCaseConferencesResponse>(`/users/${userId}/case-conferences`);
  return response.data;
};

// --- 管理確認事項 (Action Items) ---
export interface ActionItem {
  type: 'daily_log' | 'monitoring' | 'approval' | 'case_conference';
  category_label: string;
  severity: 'high' | 'medium' | 'low';
  user_id: number;
  user_name: string;
  title: string;
  description: string;
}

export interface ActionItemsResponse {
  items: ActionItem[];
}

export const fetchActionItems = async (): Promise<ActionItemsResponse> => {
  const response = await apiClient.get<ActionItemsResponse>('/action-items');
  return response.data;
};