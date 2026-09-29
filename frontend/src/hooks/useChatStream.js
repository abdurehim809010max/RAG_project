import { useState, useEffect } from 'react';
import { chatApi } from '../services/chatApi';

export function useChatStream() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch list of conversations on load
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await chatApi.getConversations();
      // Expecting array of { id, title, updated_at }
      setConversations(data.conversations || data || []);
    } catch (error) {
      console.error('Failed to load conversations list:', error);
    }
  };

  // Switch to an existing conversation
  const selectConversation = async (convId) => {
    if (convId === currentConversationId) return;
    setIsLoading(true);
    try {
      setCurrentConversationId(convId);
      const data = await chatApi.getConversationHistory(convId);
      // Map backend message format if needed
      setMessages(data.messages || data || []);
    } catch (error) {
      console.error('Failed to load conversation history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Start a brand new chat session
  const startNewChat = () => {
    setCurrentConversationId(null);
    setMessages([]);
  };

  const sendMessage = async (query) => {
    if (!query.trim() || isLoading) return;

    const userMessage = { role: 'user', content: query, sources: [] };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const data = await chatApi.sendChatQuestion(query, currentConversationId);
      
      // If this was a new chat, the backend will return a new conversation_id
      if (!currentConversationId && data.conversation_id) {
        setCurrentConversationId(data.conversation_id);
        loadConversations(); // Refresh sidebar list
      }

      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) => [
        ...prev,
        { 
          role: 'assistant', 
          content: 'ይቅርታ፣ ከሰርቨሩ ጋር በመገናኘት ላይ ስህተት ተፈጥሯል። (Error communicating with server)', 
          sources: [] 
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return { 
    conversations, 
    currentConversationId, 
    messages, 
    isLoading, 
    sendMessage, 
    selectConversation, 
    startNewChat 
  };
}