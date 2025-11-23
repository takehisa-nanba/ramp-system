// frontend/src/services/plans.ts

import apiClient from './apiClient';

// -----------------------------------------------------------
// 1. 型定義
// -----------------------------------------------------------

// 計画作成リクエストの型
export interface CreatePlanRequest {
    user_id: number;
    holistic_support_policy_id: number; // 根拠となる方針ID
}

// 個別支援目標追加リクエストの型
export interface AddGoalRequest {
    short_term_goal_id: number;
    concrete_goal: string;
    user_commitment: string;
    support_actions: string;
    service_type: string;
}

// -----------------------------------------------------------
// 2. 計画作成API
// -----------------------------------------------------------

/**
 * 新しい個別支援計画の原案(DRAFT)を作成する
 */
export const createPlanDraft = async (data: CreatePlanRequest): Promise<{plan_id: number, status: string}> => {
    // APIルートは /api/plans/
    const response = await apiClient.post<{plan_id: number, status: string}>('/plans/', data);
    return response.data;
};

/**
 * 既存の計画に個別支援目標を追加する
 */
export const addIndividualGoal = async (planId: number, data: AddGoalRequest): Promise<{goal_id: number, plan_id: number}> => {
    // APIルートは /api/plans/<plan_id>/goal です
    const response = await apiClient.post<{goal_id: number, plan_id: number}>(`/plans/${planId}/goal`, data);
    return response.data;
};