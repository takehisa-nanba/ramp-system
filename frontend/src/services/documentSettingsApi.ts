import apiClient from './apiClient';

export interface OfficeElectronicDocumentSetting {
  office_id: number;
  office_name: string;
  electronic_document_enabled: boolean;
  can_edit: boolean;
}

export interface UserElectronicDocumentSetting {
  user_id: number;
  electronic_document_opt_out: boolean;
  office_id: number;
  office_electronic_document_enabled: boolean;
  effective_policy: 'PAPER' | 'ELECTRONIC_IF_LOGIN_AVAILABLE';
  can_edit: boolean;
}

export const documentSettingsApi = {
  getOfficeSetting: async (): Promise<OfficeElectronicDocumentSetting> => {
    const response = await apiClient.get<OfficeElectronicDocumentSetting>('/consents/settings/office');
    return response.data;
  },

  updateOfficeSetting: async (electronicDocumentEnabled: boolean): Promise<OfficeElectronicDocumentSetting> => {
    const response = await apiClient.put<OfficeElectronicDocumentSetting>('/consents/settings/office', {
      electronic_document_enabled: electronicDocumentEnabled,
    });
    return response.data;
  },

  getUserSetting: async (userId: number): Promise<UserElectronicDocumentSetting> => {
    const response = await apiClient.get<UserElectronicDocumentSetting>(`/consents/settings/users/${userId}`);
    return response.data;
  },

  updateUserSetting: async (userId: number, electronicDocumentOptOut: boolean): Promise<UserElectronicDocumentSetting> => {
    const response = await apiClient.put<UserElectronicDocumentSetting>(`/consents/settings/users/${userId}`, {
      electronic_document_opt_out: electronicDocumentOptOut,
    });
    return response.data;
  },
};
