
import React, { useState } from 'react';
import Chat from './Chat';

const ChatDock = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          zIndex: 1100,
          padding: '10px 14px',
          borderRadius: '50%',
          border: 'none',
          background: '#333',
          color: '#fff',
          cursor: 'pointer'
        }}
      >
        AI
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          height: '100%',
          width: '380px',
          background: '#fff',
          borderLeft: '1px solid #ddd',
          zIndex: 1050,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <Chat onClose={() => setOpen(false)} />
        </div>
      )}
    </>
  );
};

export default ChatDock;
