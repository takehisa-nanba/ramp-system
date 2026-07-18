import api from './apiClient';

export interface SupportRecord {
  id: number;
  user_id: number;
  user_name: string;
  supporter_id: number;
  supporter_name: string;
  log_date: string;
  support_start_time?: string;
  support_end_time?: string;
  support_duration_seconds?: number;
  support_record_type: string;
  location_type?: string;
  location_detail?: string;
  support_content: string;
  decision_reason?: string;
  observation_note?: string;
}

export interface GetRecordsParams {
  start_date?: string;
  end_date?: string;
  supporter_id?: number;
  user_id?: number;
}

export interface CreateRecordPayload {
  user_id: number;
  log_date: string;
  supporter_id: number;
  support_start_time?: string;
  support_end_time?: string;
  support_duration_seconds?: number;
  support_record_type: string;
  location_type?: string;
  location_detail?: string;
  support_content: string;
  observation_note?: string;
}

export const recordsApi = {
  getRecords: async (params: GetRecordsParams): Promise<{ items: SupportRecord[] }> => {
    const response = await api.get('/records', { params });
    return response.data;
  },
  
  createRecord: async (data: CreateRecordPayload): Promise<{ msg: string; id: number }> => {
    const response = await api.post('/records', data);
    return response.data;
  }
};
