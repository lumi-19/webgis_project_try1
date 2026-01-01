import React from 'react';

const ChatMessage = ({ role, text }) => {
  const isUser = role === 'user';

  return (
    <div style={{
      textAlign: isUser ? 'right' : 'left',
      marginBottom: '8px'
    }}>
      <span style={{
        display: 'inline-block',
        padding: '8px 12px',
        borderRadius: '12px',
        background: isUser ? '#DCF8C6' : '#eee',
        maxWidth: '85%'
      }}>
        {text}
      </span>
    </div>
  );
};

export default ChatMessage;
