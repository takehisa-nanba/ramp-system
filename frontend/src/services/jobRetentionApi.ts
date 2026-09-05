// frontend/src/services/jobRetentionApi.ts

import apiClient from './apiClient';

export interface RetentionContract {
  id: number;
  user_id: number;
  user_name: string;
  contract_start_date: string;
  contract_end_date: string;
  status: 'ACTIVE' | 'TRANSITION_PENDING' | 'COMPLETED' | 'TERMINATED';
  is_company_involved: boolean;
  workplace_name?: string;
  latest_workplace?: string;
  latest_job_title?: string;
  voice_count?: number;
  action_count?: number;
  consent_status?: string;
  contract_details?: string;
  episodes?: EmploymentEpisode[];
}

export interface EmploymentEpisode {
  id: number;
  episode_number: number;
  workplace_name: string;
  job_title?: string;
  department_name?: string;
  job_start_date: string;
  job_end_date?: string | null;
  work_conditions?: string;
  resignation_reason?: string;
}

export interface UserVoiceLog {
  id?: number;
  logged_at?: string;
  raw_voice?: string;
  trouble_point?: string;
  success_point?: string;
  self_coping_action?: string;
  self_coping_result?: string;
  needs_help?: boolean;
  help_topic?: string;
}

export interface SupportActionLog {
  id?: number;
  action_date: string;
  supporter_name?: string;
  has_user_interview: boolean;
  interview_method?: string;
  has_company_visit: boolean;
  has_coordination: boolean;
  has_other_support: boolean;
  confirmed_situation: string;
  provided_support: string;
  user_action_observed?: string;
  staff_intervention_boundary?: string;
  next_step?: string;
}

export interface MonthlyRetentionReportData {
  contract_id: number;
  report_year_month: string;
  interview_records?: string;
  company_visit_records?: string;
  work_status_summary?: string;
  life_status_summary?: string;
  user_coping_summary?: string;
  employer_feedback_summary?: string;
  support_details?: string;
  future_support_policy?: string;
  status?: 'DRAFT' | 'FINALIZED';
  is_existing?: boolean;
}

export const jobRetentionApi = {
  // 契約
  async listContracts(status?: string): Promise<RetentionContract[]> {
    const params = status ? { status } : {};
    const res = await apiClient.get<RetentionContract[]>('/job-retention/contracts', { params });
    return res.data;
  },

  async getContract(contractId: number): Promise<RetentionContract> {
    const res = await apiClient.get<RetentionContract>(`/job-retention/contracts/${contractId}`);
    return res.data;
  },

  async getMyContract(): Promise<RetentionContract> {
    const res = await apiClient.get<RetentionContract>('/job-retention/my-contract');
    return res.data;
  },

  async createContract(data: any): Promise<{ id: number; msg: string }> {
    const res = await apiClient.post<{ id: number; msg: string }>('/job-retention/contracts', data);
    return res.data;
  },

  // 就労エピソード
  async addEpisode(contractId: number, data: any): Promise<{ id: number; msg: string }> {
    const res = await apiClient.post<{ id: number; msg: string }>(`/job-retention/contracts/${contractId}/episodes`, data);
    return res.data;
  },

  async endEpisode(episodeId: number, data: any): Promise<{ id: number; msg: string }> {
    const res = await apiClient.post<{ id: number; msg: string }>(`/job-retention/episodes/${episodeId}/end`, data);
    return res.data;
  },

  // 本人の声（できごと）
  async recordVoice(contractId: number, data: UserVoiceLog): Promise<{ id: number; msg: string }> {
    const res = await apiClient.post<{ id: number; msg: string }>(`/job-retention/contracts/${contractId}/voices`, data);
    return res.data;
  },

  async listVoices(contractId: number): Promise<UserVoiceLog[]> {
    const res = await apiClient.get<UserVoiceLog[]>(`/job-retention/contracts/${contractId}/voices`);
    return res.data;
  },

  // 支援記録
  async recordAction(contractId: number, data: SupportActionLog): Promise<{ id: number; msg: string }> {
    const res = await apiClient.post<{ id: number; msg: string }>(`/job-retention/contracts/${contractId}/actions`, data);
    return res.data;
  },

  async listActions(contractId: number): Promise<SupportActionLog[]> {
    const res = await apiClient.get<SupportActionLog[]>(`/job-retention/contracts/${contractId}/actions`);
    return res.data;
  },

  // 月次レポート
  async previewMonthlyReport(contractId: number, yearMonth: string): Promise<MonthlyRetentionReportData> {
    const res = await apiClient.get<MonthlyRetentionReportData>(`/job-retention/contracts/${contractId}/monthly-reports/${yearMonth}/preview`);
    return res.data;
  },

  async saveMonthlyReport(contractId: number, yearMonth: string, data: MonthlyRetentionReportData, finalize = false): Promise<{ id: number; msg: string; status: string }> {
    const res = await apiClient.post<{ id: number; msg: string; status: string }>(
      `/job-retention/contracts/${contractId}/monthly-reports/${yearMonth}`,
      { ...data, finalize }
    );
    return res.data;
  }
};
