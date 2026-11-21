import apiClient from './apiClient';

export type RetentionItem = {
  id: number; sequence_no: number; support_policy_content: string; start_date: string;
  end_date: string; frequency: string; implementation_status: string | null;
  achievement_status: string | null; effect_satisfaction_notes: string | null;
  remaining_issues_and_actions: string | null;
};
export type RetentionDetail = Record<string, unknown> & {
  job_placement_id: number | null; support_items: RetentionItem[];
};
export type Employment = { job_placement_id: number; employment_start_date: string;
  employer_name: string; industry: string | null; employer_address: string | null;
  employer_phone: string | null; employer_contact_person: string | null; employment_type: string | null };
export type RetentionResponse = {
  plan_id: number; plan_status: string; version: number; start_date: string; end_date: string;
  detail: RetentionDetail | null; employment_options: Employment[];
  permissions: { edit: boolean; create: boolean; delete: boolean; evaluate: boolean; view_pii: boolean; edit_pii: boolean };
  related_support_organizations: { id: number; name: string }[];
  organization_options: { id: number; name: string }[];
  goals: { goal_type: string; goal_id: number; description: string; start_date: string | null; end_date: string | null }[];
  goal_assessments: { goal_type: string; goal_id: number; achievement_status: string | null }[];
  assessor_types: { id: number; name: string }[];
};
export async function fetchRetentionDetail(planId: number) {
  return (await apiClient.get<RetentionResponse>(`/plans/${planId}/retention-detail`)).data;
}
export async function changeRetention(planId: number, path: string, payload: object, method: 'put' | 'post' | 'delete' = 'put') {
  return (await apiClient.request<RetentionResponse>({url: `/plans/${planId}/${path}`,method,data:payload})).data;
}
