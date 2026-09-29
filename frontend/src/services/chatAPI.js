import apiClient from './apiClient';

export const chatApi = {
  sendChatQuestion: async (query, conversationId = null) => {
    const response = await apiClient.post('/chat', { query, conversation_id: conversationId });
    return response.data;
  },
  
  // Fetch list of all past conversations
  getConversations: async () => {
    const response = await apiClient.get('/chat/conversations');
    return response.data;
  },

  // Fetch messages for a specific conversation
  getConversationHistory: async (conversationId) => {
    const response = await apiClient.get(`/chat/history/${conversationId}`);
    return response.data;
  },

  checkHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};