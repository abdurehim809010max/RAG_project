import { useState } from 'react';

export default function ChatInput({ onSendMessage, disabled }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input);
    setInput('');
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-form">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="ጥያቄዎን እዚህ ይጻፉ (Type your Amharic legal query here)..."
        disabled={disabled}
        className="chat-input"
      />
      <button type="submit" disabled={disabled || !input.trim()} className="send-btn">
        Send
      </button>
    </form>
  );
}
