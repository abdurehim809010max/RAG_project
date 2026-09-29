import apiClient from './apiClient';

export const chatApi = {
  sendChatQuestion: async (query, conversationId = null) => {
    const response = await apiClient.post('/chat', { query, conversation_id: conversationId });
    return response.data;
  },
  getConversationHistory: async (conversationId) => {
    const response = await apiClient.get(`/chat/history/${conversationId}`);
    return response.data;
  },
  checkHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};