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

export interface TimecardRecord {
  id: number;
  sequence_no: number;
  office_id: number;
  location_type: string;
  check_in: string | null;
  check_out: string | null;
  total_break_minutes: number;
}

export interface ShiftRecord {
  id: number | string;
  supporter_id: number;
  supporter_name: string;
  employment_type: string;
  job_title: string;
  target_date: string;
  planned_start_time: string | null;
  planned_end_time: string | null;
  planned_break_minutes: number;
  is_confirmed: boolean;
  actual_check_in?: string | null;
  actual_check_out?: string | null;
  total_worked_seconds?: number;
  timecards?: TimecardRecord[];
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
  generateShifts: async (year: number, month: number, supporterId?: number, aiInstruction?: string): Promise<{ msg: string, count: number }> => {
    const res = await apiClient.post(`${API_URL}/generate-shifts`, {
      year,
      month,
      supporter_id: supporterId,
      ai_instruction: aiInstruction
    });
    return res.data;
  },

  /**
   * 指定した年月のシフトを取得する
   */
  getShifts: async (year: number, month: number): Promise<{ items: ShiftRecord[] }> => {
    const res = await apiClient.get(`${API_URL}/shifts?year=${year}&month=${month}`);
    return res.data;
  },

  /**
   * 個別シフト作成 (マニュアル)
   */
  createManualShift: async (data: { supporter_id: number; target_date: string; start_time: string; end_time: string; break_minutes: number }) => {
    const res = await apiClient.post(`${API_URL}/shifts`, data);
    return res.data;
  },

  /**
   * 個別シフト更新 (マニュアル)
   */
  updateManualShift: async (shiftId: number, data: { start_time: string; end_time: string; break_minutes: number }) => {
    const res = await apiClient.put(`${API_URL}/shifts/${shiftId}`, data);
    return res.data;
  },

  /**
   * 個別シフト削除 (マニュアル)
   */
  deleteManualShift: async (shiftId: number) => {
    const res = await apiClient.delete(`${API_URL}/shifts/${shiftId}`);
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
