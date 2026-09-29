import { useRef, useEffect } from 'react';
import MessageItem from './MessageItem';
import ChatInput from './ChatInput';

export default function ChatWindow({ chatStream, onOpenMenu }) {
  const { messages, isLoading, sendMessage } = chatStream;
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Hamburger Menu Button for Mobile */}
          <button 
            onClick={onOpenMenu}
            className="mobile-menu-toggle"
            aria-label="Open Menu"
          >
            ☰
          </button>
          <div>
            <h1>Ethiopian Legal RAG Chatbot</h1>
            <p>Ask questions regarding supreme court decisions and legal files.</p>
          </div>
        </div>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <p style={{ fontWeight: '600', fontSize: '1rem' }}>No messages yet.</p>
            <p style={{ fontSize: '0.85rem', marginTop: '4px' }}>Try asking about a specific case number or legal category.</p>
          </div>
        )}
        {messages.map((msg, index) => (
          <MessageItem key={index} message={msg} />
        ))}
        {isLoading && (
          <div className="message-row assistant">
            <div className="message-bubble" style={{ color: '#8c7c6e' }}>
              Searching legal documents and generating answer...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSendMessage={sendMessage} disabled={isLoading} />
    </div>
  );
}