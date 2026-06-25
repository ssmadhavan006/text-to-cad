import React, { useState } from "react";
import StlViewer from "./components/StlViewer";
import Editor from "@monaco-editor/react";

const BACKEND_URL = "http://127.0.0.1:8000";

const EXAMPLES = [
  {
    label: "Spur Gear (Showcase Depth)",
    prompt: "design a spur gear with 12 teeth, module 2mm, 6mm bore, width 8mm, 20deg pressure angle"
  },
  {
    label: "Mounting Bracket (CSG + Fillets)",
    prompt: "design a mounting plate bracket 100mm length, 50mm width, 6mm thickness, fillet 5mm, hole 8mm, offset 15mm"
  },
  {
    label: "Primitive: Sanity Box",
    prompt: "design a cuboid box with length 40mm, width 30mm, height 20mm"
  },
  {
    label: "Gate Reject: 4-Tooth Gear",
    prompt: "design a spur gear with 4 teeth, module 2mm, 10mm width, 6mm bore"
  },
  {
    label: "Gate Reject: Impossible Hole",
    prompt: "design a plate 50mm by 50mm, 5mm thickness, with a 60mm hole in the center"
  }
];

const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);
  const [error, setError] = useState(null);
  const [isLightMode, setIsLightMode] = useState(false);
  const [sessionId, setSessionId] = useState(generateUUID());

  const [progressStage, setProgressStage] = useState("");
  const [cotText, setCotText] = useState("");
  const [codeText, setCodeText] = useState("");
  const [retryLogs, setRetryLogs] = useState([]);

  const handleGenerate = async (selectedPrompt) => {
    const activePrompt = selectedPrompt || prompt;
    if (!activePrompt.trim()) return;

    setLoading(true);
    setError(null);
    setRes(null);
    setProgressStage("Initializing pipeline...");
    setCotText("");
    setCodeText("");
    setRetryLogs([]);

    try {
      const response = await fetch(`${BACKEND_URL}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: activePrompt, session_id: sessionId, stream: true })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // Keep partial line

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            const dataStr = trimmed.slice(6);
            try {
              const parsed = JSON.parse(dataStr);
              const { event, data } = parsed;

              if (event === "stage") {
                setProgressStage(data);
              } else if (event === "cot") {
                setCotText((prev) => prev + data);
              } else if (event === "code_start") {
                setProgressStage("Streaming CadQuery script...");
              } else if (event === "code") {
                setCodeText((prev) => prev + data);
              } else if (event === "code_end") {
                setProgressStage("Executing CadQuery script...");
              } else if (event === "attempt_failed") {
                setRetryLogs((prev) => [...prev, data]);
              } else if (event === "success") {
                setRes(data);
                setProgressStage("Success! Model rendered.");
              } else if (event === "error") {
                if (typeof data === "object") {
                  setRes(data);
                  setError(data.error_message || "Self-correction exhausted.");
                } else {
                  setError(data);
                }
                setProgressStage("Failed");
              }
            } catch (jsonErr) {
              console.error("Error parsing SSE line:", line, jsonErr);
            }
          }
        }
      }
    } catch (err) {
      console.error("Fetch error:", err);
      setError(`Failed to connect to CAD server: ${err.message}`);
      setProgressStage("Failed");
    } finally {
      setLoading(false);
    }
  };

  const getModelUrl = () => {
    if (res && res.success && res.glb_file_url) {
      return `${BACKEND_URL}${res.glb_file_url}`;
    }
    return null;
  };

  const getEditorCode = () => {
    if (loading && codeText) {
      return codeText;
    }
    if (res && res.final_code) {
      return res.final_code;
    }
    return `# Generated CadQuery script will be displayed here.\n# Use the sidebar controls to run a CAD compile loop.`;
  };

  return (
    <div className="app-container">
      {/* Sidebar Section */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">
            <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5" />
            </svg>
          </div>
          <div className="logo-text">Antigravity CAD</div>
        </div>

        <div className="sidebar-content">
          {/* Session Context Status Card */}
          <div className="section-card" style={{ marginBottom: "12px", background: "rgba(30, 41, 59, 0.25)", border: "1px dashed #334155" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ fontSize: "0.7rem", textTransform: "uppercase", color: "#94a3b8", fontWeight: "600" }}>Active Context</span>
                <span style={{ fontSize: "0.85rem", color: "#e2e8f0", fontWeight: "500" }}>
                  {res && res.success ? `Editing: ${res.shape_type}` : "New Part"}
                </span>
              </div>
              <button
                onClick={() => {
                  setSessionId(generateUUID());
                  setRes(null);
                  setError(null);
                  setPrompt("");
                }}
                className="badge badge-pending"
                style={{ cursor: "pointer", border: "none", padding: "4px 8px", background: "#334155", color: "#94a3b8" }}
                title="Start a new part design and discard edit history"
              >
                Reset
              </button>
            </div>
          </div>
          {/* Quick Examples */}
          <div className="form-group">
            <label>Interactive Examples</label>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {EXAMPLES.map((ex, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setPrompt(ex.prompt);
                    handleGenerate(ex.prompt);
                  }}
                  className="btn-primary"
                  style={{
                    background: "rgba(30, 34, 48, 0.5)",
                    border: "1px solid #1e2230",
                    color: "#cbd5e1",
                    fontSize: "0.8rem",
                    padding: "8px 12px",
                    justifyContent: "flex-start",
                    textAlign: "left",
                    fontWeight: "500",
                    boxShadow: "none"
                  }}
                  disabled={loading}
                >
                  {ex.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Design Prompt</label>
            <textarea
              placeholder="e.g. design a spur gear with 12 teeth, module 2mm, 6mm bore..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
            />
          </div>

          <button
            onClick={() => handleGenerate()}
            className="btn-primary"
            disabled={loading || !prompt.trim()}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: "16px", height: "16px", borderWidth: "2px" }}></span>
                Compiling CAD...
              </>
            ) : (
              "Compile Model"
            )}
          </button>

          {/* Live Generation Console */}
          {loading && (
            <div className="section-card" style={{ borderColor: "#3b82f6", background: "rgba(59, 130, 246, 0.05)" }}>
              <div className="section-card-title" style={{ backgroundColor: "rgba(59, 130, 246, 0.15)", color: "#93c5fd" }}>
                <span>Pipeline Activity</span>
                <span className="badge badge-pending">Active</span>
              </div>
              <div className="section-card-content" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", color: "#e2e8f0" }}>
                  <span className="spinner" style={{ width: "14px", height: "14px", borderWidth: "2px" }}></span>
                  <span>{progressStage}</span>
                </div>
                
                {/* Streamed thinking logs */}
                {cotText && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <label style={{ fontSize: "0.7rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: "600" }}>Reasoning Stream</label>
                    <div 
                      style={{ 
                        fontFamily: "monospace", 
                        fontSize: "0.75rem", 
                        background: "#0f172a", 
                        color: "#10b981", 
                        padding: "8px", 
                        borderRadius: "4px", 
                        maxHeight: "120px", 
                        overflowY: "auto", 
                        whiteSpace: "pre-wrap"
                      }}
                      ref={(el) => { if (el) el.scrollTop = el.scrollHeight; }}
                    >
                      {cotText}
                    </div>
                  </div>
                )}
                
                {/* Self-correction retry warnings */}
                {retryLogs.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <label style={{ fontSize: "0.7rem", color: "#f59e0b", textTransform: "uppercase", fontWeight: "600" }}>Self-Correction Alerts</label>
                    {retryLogs.map((log, idx) => (
                      <div 
                        key={idx} 
                        style={{ 
                          fontSize: "0.75rem", 
                          background: "rgba(245, 158, 11, 0.1)", 
                          borderLeft: "3px solid #f59e0b", 
                          color: "#fde047", 
                          padding: "4px 8px" 
                        }}
                      >
                        {log}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="section-card" style={{ borderColor: "#ef4444" }}>
              <div className="section-card-title" style={{ backgroundColor: "rgba(239,68,68,0.15)", color: "#f87171" }}>
                <span>Error Log</span>
                <span className="badge badge-error">Failed</span>
              </div>
              <div className="section-card-content" style={{ fontSize: "0.85rem", color: "#fca5a5" }}>
                {error}
              </div>
            </div>
          )}

          {/* Feasibility Check Details */}
          {res && (
            <div className="section-card">
              <div className="section-card-title">
                <span>Feasibility Gate</span>
                <span className={`badge ${res.feasibility.is_feasible ? "badge-success" : "badge-error"}`}>
                  {res.feasibility.is_feasible ? "Feasible" : "Rejected"}
                </span>
              </div>
              <div className="section-card-content" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div className="step-list">
                  <div className="step-item">
                    <div className={`step-bullet ${res.feasibility.is_feasible ? "badge-success" : "badge-error"}`} />
                    <div className="step-text">
                      <strong>Shape Type:</strong> <span className="badge badge-pending">{res.shape_type}</span>
                    </div>
                  </div>
                </div>

                {res.feasibility.is_feasible ? (
                  <div>
                    <label style={{ fontSize: "0.75rem", marginBottom: "4px" }}>Normalized Parameters</label>
                    <div className="params-grid">
                      {Object.entries(res.feasibility.normalized_parameters).map(([k, v]) => (
                        <React.Fragment key={k}>
                          <span className="param-key">{k}</span>
                          <span className="param-val">
                            {typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(2)) : String(v)}
                          </span>
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <label style={{ fontSize: "0.75rem", color: "#ef4444" }}>Rejection Errors</label>
                    <ul style={{ margin: 0, paddingLeft: "16px", color: "#fca5a5", fontSize: "0.8rem", lineHeight: "1.4" }}>
                      {res.feasibility.errors.map((err, idx) => (
                        <li key={idx}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Self-Correction Retry Logs */}
          {res && res.history && res.history.length > 0 && (
            <div className="section-card">
              <div className="section-card-title">
                <span>Correction Loop ({res.attempts} / 3)</span>
                <span className={`badge ${res.success ? "badge-success" : "badge-error"}`}>
                  {res.success ? "Passed" : "Exhausted"}
                </span>
              </div>
              <div className="section-card-content" style={{ maxHeight: "250px", overflowY: "auto" }}>
                {res.history.map((hist, idx) => (
                  <div key={idx} className="history-item">
                    <div className="history-header">
                      <strong style={{ fontSize: "0.8rem" }}>Attempt {hist.attempt}</strong>
                      <span className={`badge ${hist.success ? "badge-success" : "badge-error"}`}>
                        {hist.success ? "Success" : "Failed"}
                      </span>
                    </div>
                    {!hist.success && hist.error_message && (
                      <div className="history-error">{hist.error_message}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Preview/Code Panel Section */}
      <div className="main-area">
        {/* STL Viewport */}
        <div className="viewer-section" style={{ position: "relative" }}>
          <button
            onClick={() => setIsLightMode(!isLightMode)}
            className="theme-toggle-btn"
            style={{
              position: "absolute",
              top: "12px",
              right: "12px",
              zIndex: 10,
              padding: "8px 12px",
              background: isLightMode ? "#ffffff" : "rgba(30, 34, 48, 0.75)",
              border: isLightMode ? "1px solid #cbd5e1" : "1px solid #1e2230",
              borderRadius: "6px",
              color: isLightMode ? "#1e293b" : "#cbd5e1",
              fontSize: "0.8rem",
              fontWeight: "600",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              transition: "all 0.2s ease"
            }}
          >
            {isLightMode ? (
              <>
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
                Dark Mode
              </>
            ) : (
              <>
                <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
                Light Mode
              </>
            )}
          </button>
          <StlViewer url={getModelUrl()} loading={loading} isLightMode={isLightMode} />
        </div>

        {/* Code Panel */}
        <div className="editor-section">
          <div className="editor-header">
            <div className="editor-title">Generated CadQuery Script (v1)</div>
            {res && res.success && (
              <div style={{ display: "flex", gap: "8px" }}>
                <a
                  href={`${BACKEND_URL}${res.stl_file_url}`}
                  download
                  className="badge badge-success"
                  style={{ textDecoration: "none", cursor: "pointer" }}
                >
                  Download STL
                </a>
                <a
                  href={`${BACKEND_URL}${res.step_file_url}`}
                  download
                  className="badge badge-pending"
                  style={{ textDecoration: "none", cursor: "pointer" }}
                >
                  Download STEP
                </a>
              </div>
            )}
          </div>
          <div className="editor-container">
            <Editor
              height="100%"
              defaultLanguage="python"
              theme="vs-dark"
              value={getEditorCode()}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 12,
                fontFamily: "JetBrains Mono, monospace",
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
