import MapView from "./views/MapView";
import ChatDock from "./ai/ChatDock";

export default function App() {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <div style={{ flex: 1 }}>
        <MapView />
      </div>

      <ChatDock />
    </div>
  );
}
