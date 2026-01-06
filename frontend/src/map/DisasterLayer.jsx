import { useEffect } from "react";
import L from "leaflet";

function DisasterLayer({ map }) {
  useEffect(() => {
    if (!map) return;

    let layer;

    fetch("http://127.0.0.1:8000/api/events")
      .then((res) => res.json())
      .then((geojson) => {
        console.log("Disaster GeoJSON loaded:", geojson);

        layer = L.geoJSON(geojson, {
          pointToLayer: (feature, latlng) => {
            const props = feature.properties || {};
            const type = props.event_type;
            const rawMag = props.magnitude;

            // ✅ SAFE magnitude handling
            const magnitude =
              typeof rawMag === "number" && rawMag > 0 ? rawMag : 4;

            // 🌋 Earthquakes
            if (type === "earthquake") {
              return L.circleMarker(latlng, {
                radius: Math.max(magnitude * 2, 6),
                color: "#ff6b6b",
                weight: 1,
                fillColor: "#ff3b3b",
                fillOpacity: 0.7,
              });
            }

            // 🌊 Other disasters (generic for now)
            return L.circleMarker(latlng, {
              radius: 6,
              color: "#4dabf7",
              fillColor: "#4dabf7",
              fillOpacity: 0.8,
            });
          },

          onEachFeature: (feature, layer) => {
            layer.on("click", () => {
              console.log("Disaster clicked:", feature.properties);
            });
          },
        }).addTo(map);
      })
      .catch((err) => {
        console.error("Failed to load disasters:", err);
      });

    return () => {
      if (layer) map.removeLayer(layer);
    };
  }, [map]);

  return null;
}

export default DisasterLayer;
