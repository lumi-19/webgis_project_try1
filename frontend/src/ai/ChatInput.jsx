import React, { useState } from 'react';

const ChatInput = ({ onSend }) => {
  const [value, setValue] = useState('');

  const send = () => {
    if (!value.trim()) return;
    onSend(value);
    setValue('');
  };

  return (
    <div style={{
      display: 'flex',
      padding: '10px',
      borderTop: '1px solid #ddd'
    }}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask something..."
        style={{
          flex: 1,
          padding: '8px'
        }}
      />
      <button onClick={send} style={{ marginLeft: '8px' }}>
        Send
      </button>
    </div>
  );
};

export default ChatInput;
