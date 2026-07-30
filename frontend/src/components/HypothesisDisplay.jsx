function HypothesisDisplay({ hypotheses }) {
  if (!hypotheses || hypotheses.length === 0) return null;

  // Sort by probability descending
  const sorted = [...hypotheses].sort((a, b) => b.probability - a.probability);

  return (
    <div className="hypothesis-list">
      {sorted.map((h) => {
        const pct = Math.round(h.probability * 100);
        const level = h.probability > 0.6 ? "high" : h.probability > 0.3 ? "medium" : "low";
        const statusClass = h.status === "confirmed" ? "status-confirmed"
          : h.status === "eliminated" ? "status-eliminated"
          : "status-untested";

        return (
          <div key={h.id} className="hypothesis-item">
            <span className="hypothesis-id">{h.id}</span>
            <span className="hypothesis-desc">{h.description}</span>
            <div className="hypothesis-bar-container">
              <div
                className={`hypothesis-bar ${level}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="hypothesis-prob">{h.probability.toFixed(2)}</span>
            <span className={`hypothesis-status ${statusClass}`}>
              {h.status}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default HypothesisDisplay;
