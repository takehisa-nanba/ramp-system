import apiClient from './apiClient';

const API_URL = '/dashboard/staff';

export interface StaffStatus {
  supporter_id: number;
  name: string;
  status: 'SCHEDULED' | 'WORKING' | 'FINISHED' | 'NOT_SCHEDULED';
  shift: {
    start: string | null;
    end: string | null;
  } | null;
  timecard: {
    check_in: string | null;
    check_out: string | null;
  } | null;
}

export interface ActionLog {
  id: number;
  content: string;
  timestamp: string;
  is_processed_by_ai: boolean;
}

export interface DailyReportResponse {
  msg: string;
  report_id: number;
  content: string;
}

export interface StaffStatusResponse {
  current_staff_id: number;
  staff_list: StaffStatus[];
}

export const dashboardStaffApi = {
  getStaffStatus: async (): Promise<StaffStatusResponse> => {
    const res = await apiClient.get(`${API_URL}/status`);
    return res.data;
  },
  
  addActionLog: async (content: string): Promise<{ msg: string; id: number }> => {
    const res = await apiClient.post(`${API_URL}/action-logs`, { content });
    return res.data;
  },
  
  getTodayActionLogs: async (): Promise<ActionLog[]> => {
    const res = await apiClient.get(`${API_URL}/action-logs/today`);
    return res.data;
  },
  
  generateDailyReport: async (): Promise<DailyReportResponse> => {
    const res = await apiClient.post(`${API_URL}/daily-report/generate`);
    return res.data;
  },

  clockIn: async (): Promise<{ msg: string }> => {
    const res = await apiClient.post(`${API_URL}/clock-in`);
    return res.data;
  },

  clockOut: async (breakMinutes: number = 0): Promise<{ msg: string }> => {
    const res = await apiClient.post(`${API_URL}/clock-out`, { break_minutes: breakMinutes });
    return res.data;
  },

  seedShifts: async (): Promise<{ msg: string }> => {
    const res = await apiClient.post(`${API_URL}/seed-shifts`);
    return res.data;
  }
};
