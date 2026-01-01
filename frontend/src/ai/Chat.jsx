 
import React, { useState } from 'react';
import ChatInput from './ChatInput';
import ChatMessage from './ChatMessage';

const Chat = ({ onClose }) => {
  const [messages, setMessages] = useState([
    { role: 'ai', text: 'Hello. I am DisasterScope AI (offline mode).' }
  ]);

  const handleSend = (text) => {
    setMessages([...messages, { role: 'user', text }]);
  };

  return (
    <>
      <div style={{
        padding: '10px',
        borderBottom: '1px solid #ddd',
        fontWeight: 'bold',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        AI Assistant
        <span onClick={onClose} style={{ cursor: 'pointer' }}>✕</span>
      </div>

      {/* Context placeholder */}
      <div style={{
        padding: '10px',
        fontSize: '12px',
        background: '#f5f5f5',
        borderBottom: '1px solid #ddd'
      }}>
        Context (placeholder):
        <br />
        • Current map extent  
        • Active layers  
        • Selected disaster  
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '10px'
      }}>
        {messages.map((m, i) => (
          <ChatMessage key={i} role={m.role} text={m.text} />
        ))}
      </div>

      <ChatInput onSend={handleSend} />
    </>
  );
};

export default Chat;
