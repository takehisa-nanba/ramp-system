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