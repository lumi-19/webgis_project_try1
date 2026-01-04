

# 🌋 DISASTERSCOPE

**AI-Assisted WebGIS for Real-Time Disaster Intelligence**

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-FastAPI-green?logo=python)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-17+-blue?logo=react)](https://reactjs.org/)

> **Building resilience through open-source intelligence.**

DISASTERSCOPE is a local-first, Dockerized, and open-source platform that transforms static maps into predictive, AI-driven narratives for disaster preparedness and response.

---

## 📖 Table of Contents

- [Overview](#-overview)
- [🚀 Quick Start](#-quick-start)
- [🏗️ System Architecture](#️-system-architecture)
- [🐳 Docker Compose](#-docker-compose)
- [⚙️ Backend API (FastAPI)](#️-backend-api-fastapi)
- [🌐 Frontend UI](#-frontend-ui)
- [🤖 AI Map Assistant](#-ai-map-assistant)
- [📄 License](#-license)

---

## 📖 Overview

DISASTERSCOPE is an open-source WebGIS platform that integrates real-time disaster data with AI-powered insights. Designed for emergency responders, researchers, and civic technologists, it delivers actionable intelligence on floods, wildfires, earthquakes, and storms through an intuitive, offline-capable interface.

**Key Capabilities:**
- **Real-time Visualization:** Global disaster events from trusted sources like NASA, USGS, FIRMS, and NOAA.
- **Natural Language Queries:** Interact with the map using an on-device AI assistant.
- **Predictive Analytics:** Get risk assessments with confidence scoring to anticipate future threats.
- **Local-First Operation:** Works fully offline after the initial data sync, ensuring reliability during critical infrastructure outages.
- **100% Open-Source:** Free to use, modify, and distribute, fostering a community-driven approach to resilience.

---

## 🚀 Quick Start

Get DISASTERSCOPE running on your local machine in minutes with Docker Compose.

1.  **Clone the repository**
    ```bash
    git clone https://github.com/yourname/disasterscope.git
    cd disasterscope
    ```

2.  **Configure environment**
    ```bash
    cp .env.example .env
    ```
    > (Optional) Review and edit the `.env` file to customize ports, API keys, or other settings.

3.  **Launch the stack**
    ```bash
    docker compose up --build -d
    ```
    The `-d` flag runs the containers in detached mode. This process may take a few minutes on the first run as it downloads images, builds the application, and ingests initial data.

### Access the Application
Once running, you can access the services at the following default URLs:
- **🌐 Web UI**: [http://localhost:3000](http://localhost:3000)
- **📚 API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **🗺️ GeoServer**: [http://localhost:8080/geoserver](http://localhost:8080/geoserver)

---

## 🏗️ System Architecture

DISASTERSCOPE follows a modular, containerized architecture optimized for scalability, privacy, and performance. Each component runs in its own Docker container, orchestrated by Docker Compose.

```text
================================================================================
  🌋 DISASTERSCOPE | AI-Assisted WebGIS for Real-Time Disaster Intelligence 🌪️
================================================================================

  [ VISION ]  Local-first, Dockerized, and Open-Source.
              Transforming static maps into predictive, AI-driven narratives.

  [ SYSTEM ARCHITECTURE ]
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           USER INTERFACE                               │
  │      React + Leaflet (2D Map) | Chart.js (Trends) | Framer Motion      │
  └───────────────────────────────┬────────────────────────────────────────┘
                                  │ REST / WebSockets
  ┌───────────────────────────────▼────────────────────────────────────────┐
  │                        FASTAPI GATEWAY (Python)                        │
  │       Auth • Data Fusion • AI Agent Orchestration • Task Queue         │
  └───────┬───────────────────────┬───────────────────────┬────────────────┘
          │                       │                       │
  ┌───────▼───────┐       ┌───────▼───────┐       ┌───────▼────────┐
  │    POSTGIS    │       │    REDIS      │       │   GEOSERVER    │
  │  (Spatial DB) │       │   (Caching)   │       │  (WMS / WFS)   │
  └───────┬───────┘       └───────┬───────┘       └───────┬────────┘
          │                       │                       │
  ┌───────▼───────────────────────▼───────────────────────▼────────┐
  │                          DOCKER COMPOSE STACK                          │
  └────────────────────────────────────────────────────────────────────────┘
```

### Core Components
-   **Frontend**: A responsive [React](https://reactjs.org/) application with [Leaflet](https://leafletjs.com/) for interactive mapping, [Chart.js](https://www.chartjs.org/) for data visualization, and [Framer Motion](https://www.framer.com/motion/) for smooth UI transitions.
-   **Backend Gateway**: A high-performance [FastAPI](https://fastapi.tiangolo.com/) server that handles authentication, data fusion, AI orchestration, and asynchronous task management.
-   **Data Layer**:
    -   **PostGIS**: A powerful PostgreSQL extension for storing and querying geospatial data.
    -   **Redis**: An in-memory data store used for caching API responses and managing a background task queue.
    -   **GeoServer**: An open-source server for sharing geospatial data via standard OGC protocols like WMS and WFS.
-   **AI Engine**: Runs locally via [Ollama](https://ollama.ai/) or GPT4All for privacy-preserving natural language understanding.

---

## 🐳 Docker Compose

The entire stack is defined in `docker-compose.yml`, enabling a simple, reproducible deployment process.

### Services
-   `frontend`: React app (port `3000`)
-   `backend`: FastAPI server (port `8000`)
-   `postgis`: PostgreSQL + PostGIS database (port `5432`)
-   `redis`: In-memory cache and message broker (port `6379`)
-   `geoserver`: OGC-compliant map server (port `8080`)
-   `ollama`: Local LLM runtime (port `11434`)

> **Note**: Initial data ingestion (e.g., USGS earthquake feeds, FIRMS fire alerts) runs automatically on first startup.

---

## ⚙️ Backend API (FastAPI)

The FastAPI gateway serves as the system’s nerve center, providing a robust and modern interface for all client interactions.

### Features
-   **RESTful Endpoints**: For fetching disaster data, managing users, and handling AI queries.
-   **WebSocket Support**: For real-time event streaming, such as new wildfire alerts or earthquake updates.
-   **Task Queue**: Leverages Redis and Celery for asynchronous data processing and model inference, preventing API timeouts.
-   **Data Fusion Pipeline**: Normalizes disparate sources (GeoJSON, CSV, WFS) into a unified PostGIS schema for seamless analysis.

### Example Endpoints
-   `GET /api/v1/disasters?type=flood&year=2023`
-   `POST /api/v1/ai/query` with body: `{ "prompt": "Predict next fire risk in California" }`
-   `GET /api/v1/layers` to retrieve available WMS layer metadata.

Authentication is JWT-based with optional OAuth2 integration (e.g., GitHub, Google).

---

## 🌐 Frontend UI

Built with modern web technologies, the UI is optimized for performance, accessibility, and compelling data storytelling.

### Key Components
-   **Interactive Map**: A Leaflet-based viewer with layer toggles for floods, fires, quakes, and storms.
-   **Time Slider**: Replay historical events across customizable date ranges to understand patterns.
-   **AI Assistant Panel**: A chat-like interface for asking natural language questions about the map.
-   **Analytics Dashboard**: Trend charts showing event frequency, severity, and predicted risk over time.
-   **Layer Stories**: Guided narratives that combine maps, timelines, and explanatory text.

The application is fully responsive and PWA-enabled, allowing it to be installed on devices for reliable offline use.

---

## 🤖 AI Map Assistant

The AI Assistant provides a natural language interface to the platform's powerful analytical capabilities, running entirely on-device for privacy and reliability.

### Capabilities
-   **Query Understanding**: Parses intent from phrases like *"Show me all floods in Bangladesh from 2023"*.
-   **Predictive Requests**: Handles prompts like *"Where is the next wildfire most likely to ignite?"* using embedded risk models.
-   **Confidence Scoring**: Returns insights with uncertainty estimates (e.g., *"72% confidence in a high-risk zone"*).
-   **Offline Operation**: Runs locally via Ollama or GPT4All, with no dependency on cloud APIs.

The assistant is context-aware, able to reference current map bounds, selected layers, and active time filters to provide highly relevant results.

---

## 📄 License

DISASTERSCOPE is **100% Free and Open Source**.

-   **Code**: Licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html).
-   **Data**: All integrated datasets are from open public sources (NASA, USGS, NOAA, etc.) and retain their original licenses.
-   **Philosophy**: We believe disaster intelligence should be accessible, transparent, and community-driven.

> We welcome contributions! Please see our `CONTRIBUTING.md` for guidelines.

---

**Build resilience. Share knowledge. Stay prepared.** 🌍
