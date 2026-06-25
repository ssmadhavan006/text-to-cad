# Text-to-CAD Web Console

This is the React client dashboard for the Text-to-CAD engine. It provides a visual 3D canvas, a console logging generator stages and reasoning tokens, and an interactive code editor.

---

## 🎨 Features

* **Real-time Generation console**: Lists active pipeline stages (`Intent extraction`, `RAG retrieval`, `CAD compilation`), outputs retry alerts, and streams Chain-of-Thought (thinking) logs in real-time.
* **Vibrant Glassmorphic UI**: Premium responsive UI with theme-aware colors (Light Mode / Dark Mode).
* **WebGL 3D Viewport**: Uses Three.js (React Three Fiber) to render size-aware binary `.glb` meshes with smooth shading, eliminating low-resolution faceting on curved geometries.
* **Monaco Code panel**: Feeds code tokens dynamically into a Monaco editor frame as they are generated, letting users inspect and edit Python scripts before manual exports.
* **Active Session Context**: Tracks backend session state for multi-turn modifications, showing active session IDs, merged parameters, and a "Reset Session" button.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Run the Local Development Server
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🛠️ Configuration
The React application connects to the FastAPI backend at `http://127.0.0.1:8000`. You can configure the API endpoint inside `frontend/src/App.jsx` under the `BASE_URL` constant.
