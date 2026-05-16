import apiClient from './apiClient';

export interface AttendanceStatus {
  status: 'IDLE' | 'WORKING' | 'COMPLETED';
  check_in: string | null;
  check_out: string | null;
}

export const attendanceApi = {
  getStatus: async (): Promise<AttendanceStatus> => {
    const response = await apiClient.get('/attendance/status');
    return response.data;
  },

  clockIn: async (location?: string): Promise<{ time: string }> => {
    const response = await apiClient.post('/attendance/clock-in', { location });
    return response.data;
  },

  clockOut: async (location?: string): Promise<{ time: string }> => {
    const response = await apiClient.post('/attendance/clock-out', { location });
    return response.data;
  }
};
