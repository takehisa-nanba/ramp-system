import apiClient from './apiClient';

export interface UserStatus {
  attendance_status: 'IDLE' | 'CLOCKED_IN' | 'CLOCKED_OUT';
  last_record_time: string | null;
  has_morning_log: boolean;
  has_evening_log: boolean;
  log_config?: {
    morning_fields: Array<{ id: string; label: string; type: 'score' | 'text' | 'time' | 'number'; required: boolean }>;
    evening_fields: Array<{ id: string; label: string; type: 'score' | 'text' | 'time' | 'number'; required: boolean }>;
  };
}



export interface UserGoal {
  id: number;
  content: string;
  priority: number;
}

export interface DailyLogSubmission {
  physical_condition_score?: number;
  sleep_quality_score?: number;
  user_self_evaluation?: string;
  custom_data?: Record<string, any>;
  morning_completed?: boolean;
  evening_completed?: boolean;
}


export const userSupportApi = {
  getStatus: async (): Promise<UserStatus> => {
    const response = await apiClient.get('/user/status');
    return response.data;
  },

  recordAttendance: async (type: 'CHECK_IN' | 'CHECK_OUT', location?: string) => {
    const response = await apiClient.post('/user/attendance', { type, location });
    return response.data;
  },

  submitDailyLog: async (data: DailyLogSubmission) => {
    const response = await apiClient.post('/user/daily-log', data);
    return response.data;
  },

  getGoals: async (): Promise<{ goals: UserGoal[] }> => {
    const response = await apiClient.get('/user/goals');
    return response.data;
  }
};
