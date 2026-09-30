import { useState } from 'react';
import ChatWindow from './components/chat/ChatWindow';
import { useChatStream } from './hooks/useChatStream';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  const chatStream = useChatStream();

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setIsMobileMenuOpen(false);
  };

  return (
    <div className="app-container">
      {/* Mobile Sidebar Overlay */}
      <div 
        className={`sidebar-overlay ${isMobileMenuOpen ? 'active' : ''}`}
        onClick={() => setIsMobileMenuOpen(false)}
      />

      {/* Sidebar Navigation */}
      <aside className={`sidebar ${isMobileMenuOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Legal RAG System</span>
          <button 
            onClick={() => setIsMobileMenuOpen(false)}
            className="mobile-only-close"
            style={{ background: 'none', border: 'none', color: '#d1c4b2', fontSize: '1.2rem', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        <div style={{ padding: '15px', display: 'flex', flexDirection: 'column', height: 'calc(100% - 70px)', boxSizing: 'border-box' }}>
          {/* New Chat Button */}
          <button 
            onClick={() => {
              chatStream.startNewChat();
              setIsMobileMenuOpen(false);
            }} 
            className="new-chat-btn"
          >
            + New Legal Query
          </button>

          <nav className="sidebar-nav" style={{ padding: '0 0 15px 0' }}>
            <button
              onClick={() => handleTabChange('chat')}
              className={`nav-btn ${activeTab === 'chat' ? 'active' : ''}`}
              style={{ width: '100%' }}
            >
              Chat Assistant
            </button>
            <button
              onClick={() => handleTabChange('upload')}
              className={`nav-btn ${activeTab === 'upload' ? 'active' : ''}`}
              style={{ width: '100%' }}
            >
              Document Management
            </button>
          </nav>

          {/* Chat History List */}
          {activeTab === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
              <div className="history-section-title">Recent Inquiries</div>
              <div className="history-list">
                {chatStream.conversations.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: '#8c7c6e', padding: '8px' }}>No past inquiries found.</div>
                ) : (
                  chatStream.conversations.map((conv) => (
                    <button
                      key={conv.id || conv.conversation_id}
                      onClick={() => {
                        chatStream.selectConversation(conv.id || conv.conversation_id);
                        setIsMobileMenuOpen(false);
                      }}
                      className={`history-item ${(chatStream.currentConversationId === (conv.id || conv.conversation_id)) ? 'active' : ''}`}
                    >
                      {conv.title || conv.query || 'Legal Inquiry'}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Pane */}
      <main className="main-content">
        {activeTab === 'chat' && <ChatWindow chatStream={chatStream} onOpenMenu={() => setIsMobileMenuOpen(true)} />}
        {activeTab === 'upload' && (
          <div className="upload-view">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <button 
                onClick={() => setIsMobileMenuOpen(true)}
                className="mobile-menu-toggle"
                aria-label="Open Menu"
              >
                ☰
              </button>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0, color: '#3b2314' }}>Document Ingestion Hub</h2>
            </div>
            <p style={{ color: '#78685b' }}>Document upload components are handled by Person 3.</p>
          </div>
        )}
      </main>
    </div>
  );
}