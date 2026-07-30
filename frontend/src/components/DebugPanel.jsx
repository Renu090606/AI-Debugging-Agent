import { useState } from "react";
import HypothesisDisplay from "./HypothesisDisplay";

function DebugPanel({ status, result, error, onAnswer }) {
  const [answer, setAnswer] = useState("");

  if (status === "idle") {
    return (
      <div className="debug-panel-idle">
        <p>
          Paste your Python code and traceback, then click <strong>Debug</strong> to start the AI agent.
          <br /><br />
          The agent will generate hypotheses, run static analysis tools, and identify the root cause.
        </p>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="debug-panel-loading">
        <div className="spinner" />
        <span className="loading-text">Agent is analyzing your code...</span>
      </div>
    );
  }

  if (status === "error") {
    return <div className="error-message">{error}</div>;
  }

  if (!result) return null;

  const handleSendAnswer = () => {
    if (answer.trim()) {
      onAnswer(answer.trim());
      setAnswer("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && answer.trim()) {
      handleSendAnswer();
    }
  };

  // Clean suggested fix (remove markdown fences if present)
  const cleanFix = (fix) => {
    if (!fix) return "";
    return fix
      .replace(/^```python\n?/m, "")
      .replace(/^```\n?/m, "")
      .replace(/\n?```$/m, "")
      .trim();
  };

  return (
    <div className="debug-panel-results">
      {/* Conclusion */}
      {result.conclusion && (
        <div className="result-section">
          <div className="result-section-header">
            <span>Conclusion</span>
            {result.confidence_level && (
              <span className={`confidence-badge confidence-${result.confidence_level}`}>
                {result.confidence_level} ({(result.confidence * 100).toFixed(0)}%)
              </span>
            )}
          </div>
          <p className="conclusion-text">{result.conclusion}</p>
        </div>
      )}

      {/* Suggested Fix */}
      {result.suggested_fix && (
        <div className="result-section">
          <div className="result-section-header">Suggested Fix</div>
          <pre className="fix-block">{cleanFix(result.suggested_fix)}</pre>
        </div>
      )}

      {/* Hypotheses */}
      {result.hypotheses && result.hypotheses.length > 0 && (
        <div className="result-section">
          <div className="result-section-header">Hypotheses</div>
          <HypothesisDisplay hypotheses={result.hypotheses} />
        </div>
      )}

      {/* Reasoning Chain */}
      {result.reasoning_chain && result.reasoning_chain.length > 0 && (
        <div className="result-section">
          <div className="result-section-header">
            Reasoning Chain ({result.reasoning_chain.length} steps)
          </div>
          <ul className="reasoning-list">
            {result.reasoning_chain.map((step, i) => (
              <li key={i} className="reasoning-item">{step}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Question from Agent */}
      {status === "question" && result.question && (
        <div className="question-section">
          <p className="question-text">
            <strong>Agent asks:</strong> {result.question}
          </p>
          <div className="question-input-row">
            <input
              className="question-input"
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your answer..."
              autoFocus
            />
            <button className="send-btn" onClick={handleSendAnswer}>
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default DebugPanel;
