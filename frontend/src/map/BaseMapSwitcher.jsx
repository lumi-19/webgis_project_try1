 
import React from 'react';

const BaseMapSwitcher = ({ baseMap, setBaseMap }) => {
  const buttonStyle = {
    padding: '8px 12px',
    margin: '5px',
    backgroundColor: 'white',
    border: '1px solid #ccc',
    borderRadius: '4px',
    cursor: 'pointer',
    boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
  };

  const activeStyle = {
    ...buttonStyle,
    backgroundColor: '#4CAF50',
    color: 'white',
    fontWeight: 'bold'
  };

  return (
    <div style={{
      position: 'absolute',
      top: '20px',
      right: '20px',
      zIndex: 1000,
      backgroundColor: 'white',
      padding: '10px',
      borderRadius: '5px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
    }}>
      <div style={{ marginBottom: '5px', fontWeight: 'bold' }}>Base Map</div>
      <div>
        <button
          style={baseMap === 'OpenStreetMap' ? activeStyle : buttonStyle}
          onClick={() => setBaseMap('OpenStreetMap')}
        >
          Street
        </button>
        <button
          style={baseMap === 'Terrain' ? activeStyle : buttonStyle}
          onClick={() => setBaseMap('Terrain')}
        >
          Terrain
        </button>
        <button
          style={baseMap === 'Satellite' ? activeStyle : buttonStyle}
          onClick={() => setBaseMap('Satellite')}
        >
          Satellite
        </button>
      </div>
    </div>
  );
};

export default BaseMapSwitcher;