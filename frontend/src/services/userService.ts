// frontend/src/services/userService.ts

import apiClient from './apiClient';

// APIから返ってくるデータの型定義
export interface UserPiiResponse {
  id: number;
  display_name: string;
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

/**
 * 指定した利用者のPIIを取得する
 * (VIEW_PII 権限が必要)
 */
export const fetchUserPii = async (userId: number): Promise<UserPiiResponse> => {
  const response = await apiClient.get<UserPiiResponse>(`/users/${userId}/pii`);
  return response.data;
};