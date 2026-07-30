import { useState, useEffect } from "react";
import CodeEditor from "./components/CodeEditor";
import DebugPanel from "./components/DebugPanel";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [code, setCode] = useState("# Paste your Python code here\n");
  const [traceback, setTraceback] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | done | error | question
  const [result, setResult] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");

  const canDebug = code.trim().length > 0 && traceback.trim().length > 0 && status !== "loading";

  const handleDebug = async () => {
    setStatus("loading");
    setResult(null);
    setError(null);
    setSessionId(null);

    try {
      const res = await fetch(`${API_URL}/debug`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, traceback }),
      });

      if (!res.ok && res.status === 422) {
        const data = await res.json();
        setStatus("error");
        setError("Invalid input: " + (data.detail?.[0]?.msg || "Check your code and traceback"));
        return;
      }

      const data = await res.json();

      if (data.error) {
        setStatus("error");
        setError(data.error);
      } else if (data.status === "pending_question") {
        setStatus("question");
        setSessionId(data.session_id);
        setResult(data);
      } else {
        setStatus("done");
        setResult(data);
      }
    } catch (err) {
      setStatus("error");
      setError("Cannot connect to backend. Make sure the server is running on " + API_URL);
    }
  };

  const handleAnswer = async (answer) => {
    setStatus("loading");

    try {
      const res = await fetch(`${API_URL}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, answer }),
      });

      const data = await res.json();

      if (data.error) {
        setStatus("error");
        setError(data.error);
      } else if (data.status === "pending_question") {
        setStatus("question");
        setSessionId(data.session_id);
        setResult(data);
      } else {
        setStatus("done");
        setResult(data);
      }
    } catch (err) {
      setStatus("error");
      setError("Connection lost. Please try again.");
    }
  };

  const handleReset = () => {
    setStatus("idle");
    setResult(null);
    setError(null);
    setSessionId(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>AI Debugging Agent</h1>
        <span className="app-subtitle">ReAct-based Python error diagnosis</span>
        <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "dark" ? "\u2600\uFE0F" : "\uD83C\uDF19"}
        </button>
      </header>

      <main className="app-main">
        <section className="input-section">
          <div className="editor-container">
            <label className="section-label">Python Code</label>
            <CodeEditor value={code} onChange={setCode} theme={theme} />
          </div>

          <div className="traceback-container">
            <label className="section-label">Traceback / Error</label>
            <textarea
              className="traceback-input"
              value={traceback}
              onChange={(e) => setTraceback(e.target.value)}
              placeholder="Paste your Python traceback here...&#10;&#10;Example:&#10;Traceback (most recent call last):&#10;  File &quot;main.py&quot;, line 2, in <module>&#10;    result = x + y&#10;NameError: name 'y' is not defined"
              spellCheck={false}
            />
          </div>

          <div className="actions">
            <button
              className="debug-btn"
              onClick={handleDebug}
              disabled={!canDebug}
            >
              {status === "loading" ? "Debugging..." : "Debug"}
            </button>
            {status !== "idle" && status !== "loading" && (
              <button className="reset-btn" onClick={handleReset}>
                Reset
              </button>
            )}
          </div>
        </section>

        <section className="output-section">
          <DebugPanel
            status={status}
            result={result}
            error={error}
            onAnswer={handleAnswer}
          />
        </section>
      </main>
    </div>
  );
}

export default App;
