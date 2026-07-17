import api from './apiClient';

export interface AIGatewayTestRequest {
  prompt: string;
  use_pro?: boolean;
}

export interface AIGatewayTestResponse {
  success: boolean;
  response?: string;
  model_used?: string;
  error?: string;
}

export const aiGatewayService = {
  testGateway: async (data: AIGatewayTestRequest): Promise<AIGatewayTestResponse> => {
    try {
      const response = await api.post('/ai-gateway/test', data);
      return response.data;
    } catch (error: any) {
      console.error('AI Gateway Test Error:', error);
      return {
        success: false,
        error: error.response?.data?.error || '通信エラーが発生しました',
      };
    }
  },
};
