
const API_BASE = "/api";

async function request(endpoint) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Request failed: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API error (${endpoint}):`, err);
    throw err;
  }
}

export function getHealth() {
  return request("/health");
}

export function getEvents() {
  return request("/events");
}

export function getAirQuality() {
  return request("/air-quality");
}

export function getPredictionSummary() {
  return request("/predictions/summary");
}
