import apiClient from './apiClient';

export interface MyPageTodayResponse {
  attendance: {
    checked_in: boolean;
    check_in_time: string | null;
    checked_out: boolean;
    check_out_time: string | null;
  };
  daily_log: {
    physical_condition_score: number | null;
    sleep_quality_score: number | null;
    user_self_evaluation: string | null;
  };
}

export const getMyPageToday = async (): Promise<MyPageTodayResponse> => {
  const response = await apiClient.get('/user/status');
  return response.data;
};

export const postMyPageAttendance = async (recordType: 'CHECK_IN' | 'CHECK_OUT'): Promise<void> => {
  await apiClient.post('/user/attendance', { type: recordType });
};

export const postMyPageDailyLog = async (data: {
  physical_condition_score: number;
  sleep_quality_score: number;
  user_self_evaluation: string;
}): Promise<void> => {
  await apiClient.post('/user/daily-log', data);
};
