 
import React from 'react';

const StatusBar = ({ position }) => {
  const statusStyle = {
    position: 'absolute',
    bottom: '0',
    left: '0',
    right: '0',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    color: 'white',
    padding: '8px 15px',
    fontSize: '14px',
    zIndex: 1000
  };

  return (
    <div style={statusStyle}>
      {position
        ? `Lat: ${position.lat.toFixed(5)} | Lng: ${position.lng.toFixed(5)}`
        : 'Move cursor over map'}
    </div>
  );
};

export default StatusBar;
