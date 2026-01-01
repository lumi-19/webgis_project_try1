import React, { useState } from 'react';
import { MapContainer, TileLayer, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import BaseMapSwitcher from './BaseMapSwitcher';
import StatusBar from './StatusBar';
import LayerPanel from './LayerPanel';

// Component to handle map events
const MapEvents = ({ onMove }) => {
  useMapEvents({
    mousemove: (e) => {
      onMove(e.latlng);
    },
  });
  return null;
};

const Map = () => {
  const [cursorPosition, setCursorPosition] = useState(null);
  const [baseMap, setBaseMap] = useState('OpenStreetMap');

  const handleMouseMove = (latlng) => {
    setCursorPosition({ lat: latlng.lat, lng: latlng.lng });
  };

  const getTileLayerConfig = () => {
    switch (baseMap) {
      case 'Terrain':
        return {
          url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
          attribution: '© OpenTopoMap contributors',
        };
      case 'Satellite':
        return {
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          attribution: '© Esri, Maxar, Earthstar Geographics',
        };
      default:
        return {
          url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          attribution: '© OpenStreetMap contributors',
        };
    }
  };

  const tileConfig = getTileLayerConfig();

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <MapContainer
        center={[30, 70]}
        zoom={5}
        style={{ width: '100%', height: '100%' }}
      >
        <TileLayer
          url={tileConfig.url}
          attribution={tileConfig.attribution}
        />

        <MapEvents onMove={handleMouseMove} />
      </MapContainer>

      <BaseMapSwitcher baseMap={baseMap} setBaseMap={setBaseMap} />
      <StatusBar position={cursorPosition} />
      <LayerPanel />
    </div>
  );
};

export default Map;
