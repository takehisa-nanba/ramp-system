import apiClient from './apiClient';

export type InterviewMethod = 'IN_PERSON' | 'VIDEO' | 'PHONE';

export interface Interview {
  interview_date: string;
  method: InterviewMethod;
  summary: string;
  exception_reason?: string | null;
}

export interface PlanAssessment extends Interview {
  id: number;
  plan_id: number | null;
}

export async function fetchPlanAssessments(userId: number, configId?: number) {
  const result = await apiClient.get<PlanAssessment[]>(`/users/${userId}/plan-assessments`, {
    params: { office_service_configuration_id: configId },
  });
  return result.data;
}

export async function savePlanAssessment(userId: number, configId: number | undefined, interview: Interview, planId?: number) {
  await apiClient.post(`/users/${userId}/plan-assessments`, { ...interview, plan_id: planId }, {
    params: { office_service_configuration_id: configId },
  });
}
