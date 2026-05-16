import apiClient from './apiClient';

export interface FormField {
  id: string;
  label: string;
  type: 'score' | 'text' | 'time' | 'number';
  required: boolean;
  score_style?: 'emoji' | 'numbers'; // 5段階評価のスタイル
}


export interface LogSettings {
  morning_fields: FormField[];
  evening_fields: FormField[];
}


export const staffSettingsApi = {
  getDailyLogSettings: async (): Promise<LogSettings> => {
    const response = await apiClient.get('/staff/settings/daily-log');
    return response.data;
  },

  updateDailyLogSettings: async (settings: LogSettings): Promise<void> => {
    await apiClient.put('/staff/settings/daily-log', settings);
  }
};
