 
import React from 'react';

const LayerPanel = () => {
  const panelStyle = {
    position: 'absolute',
    top: '20px',
    left: '20px',
    width: '250px',
    backgroundColor: 'white',
    padding: '15px',
    borderRadius: '5px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
    zIndex: 1000
  };

  return (
    <div style={panelStyle}>
      <h3 style={{ marginTop: '0', marginBottom: '15px' }}>Layers</h3>
      <div style={{ color: '#666', fontStyle: 'italic' }}>
        Layer functionality will be implemented here.
      </div>
      <div style={{ marginTop: '15px' }}>
        <div style={{ padding: '8px', backgroundColor: '#f5f5f5', borderRadius: '3px', marginBottom: '5px' }}>
          <input type="checkbox" disabled /> Disaster Zones
        </div>
        <div style={{ padding: '8px', backgroundColor: '#f5f5f5', borderRadius: '3px', marginBottom: '5px' }}>
          <input type="checkbox" disabled /> Population Density
        </div>
        <div style={{ padding: '8px', backgroundColor: '#f5f5f5', borderRadius: '3px' }}>
          <input type="checkbox" disabled /> Infrastructure
        </div>
      </div>
    </div>
  );
};

export default LayerPanel;