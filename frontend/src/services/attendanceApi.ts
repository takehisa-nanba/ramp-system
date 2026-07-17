// frontend/src/services/attendanceApi.ts

import apiClient from './apiClient';

const API_URL = '/attendance';

export interface ShiftPattern {
  id: number;
  supporter_id: number;
  day_of_week: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
}

export interface AttendanceCorrectionRequest {
  id: number;
  target_date: string;
  record_type: string;
  request_status: string;
  request_reason: string;
}

export const attendanceApi = {
  /**
   * 基本シフトパターンから指定月のシフトを一括生成する
   */
  generateShifts: async (year: number, month: number, supporterId?: number): Promise<{ msg: string, count: number }> => {
    const res = await apiClient.post(`${API_URL}/generate-shifts`, {
      year,
      month,
      supporter_id: supporterId
    });
    return res.data;
  },

  /**
   * 管理者による直接タイムカード編集（Decisionの強制適用）
   */
  directEditTimecard: async (
    timecardId: number, 
    data: {
      check_in?: string | null;
      check_out?: string | null;
      break_minutes?: number;
      is_absent?: boolean;
      absence_type?: string | null;
    }
  ): Promise<{ msg: string, deemed_work_minutes?: number }> => {
    const res = await apiClient.put(`${API_URL}/timecards/${timecardId}`, data);
    return res.data;
  },

  /**
   * 勤怠修正（休暇等含む）の申請を送信する
   */
  submitCorrectionRequest: async (
    targetDate: string,
    recordType: string,
    reason: string
  ): Promise<{ msg: string, id: number }> => {
    const res = await apiClient.post(`${API_URL}/requests`, {
      target_date: targetDate,
      record_type: recordType,
      reason
    });
    return res.data;
  }
};
