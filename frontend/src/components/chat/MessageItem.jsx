import CitationCard from './CitationCard';

export default function MessageItem({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-bubble">
        <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div style={{ marginTop: '12px', borderTop: '1px solid #e2e8f0', paddingTop: '8px' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', marginBottom: '4px' }}>
              Legal Sources / Citations:
            </div>
            {message.sources.map((source, idx) => (
              <CitationCard key={idx} source={source} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}