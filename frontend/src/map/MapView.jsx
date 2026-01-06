import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import DisasterLayer from "./DisasterLayer";

function MapView() {
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const [map, setMap] = useState(null);

  useEffect(() => {
    if (mapRef.current) return;

    const leafletMap = L.map(containerRef.current, {
      center: [20, 0],
      zoom: 2,
      minZoom: 2,
      worldCopyJump: true,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        subdomains: "abcd",
        maxZoom: 19,
      }
    ).addTo(leafletMap);

    mapRef.current = leafletMap;
    setMap(leafletMap);
  }, []);

  return (
    <>
      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%", background: "#0b0f14" }}
      />
      <DisasterLayer map={map} />
    </>
  );
}

export default MapView;
