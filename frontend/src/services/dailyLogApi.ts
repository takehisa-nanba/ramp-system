import apiClient from './apiClient';

export interface ActivityTag {
  id: number;
  name: string;
  is_direct_support: boolean;
}

export interface UserSummary {
  id: number;
  display_name: string;
}

export interface ActivityLogEntry {
  tag_id: number;
  user_id?: number;
  start_time: string; // ISO
  end_time: string;   // ISO
  duration_minutes: number;
  notes?: string;
}

export interface TimelineEntry {
  type: 'support' | 'office';
  title: string;
  user?: string;
  startTime: string;
  endTime: string;
  duration?: number;
  notes?: string;
}

export const dailyLogApi = {
  // 活動タグ一覧の取得
  getTags: async (): Promise<ActivityTag[]> => {
    const response = await apiClient.get<ActivityTag[]>('/activities/tags');
    return response.data;
  },

  // 利用者一覧の取得（ドロップダウン用）
  getUsers: async (): Promise<UserSummary[]> => {
    const response = await apiClient.get<UserSummary[]>('/users');
    return response.data;
  },

  // 活動の記録（保存）
  logActivity: async (entry: ActivityLogEntry) => {
    const response = await apiClient.post('/activities/log', entry);
    return response.data;
  },

  // 本日のタイムライン取得
  getTodayTimeline: async (): Promise<TimelineEntry[]> => {
    const response = await apiClient.get<TimelineEntry[]>('/activities/today');
    return response.data;
  },
};
