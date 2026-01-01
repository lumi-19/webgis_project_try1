 
export default function Prediction({ data }) {
  if (!data) {
    return <div>No prediction data available.</div>;
  }

  const { risk_level, summary, counts, trend } = data;

  return (
    <div style={{ padding: "1rem" }}>
      <h2>Risk Summary</h2>

      {risk_level && (
        <p>
          <strong>Overall Risk Level:</strong> {risk_level}
        </p>
      )}

      {summary && (
        <p style={{ marginTop: "1rem" }}>{summary}</p>
      )}

      {counts && (
        <>
          <h3>Event Counts</h3>
          <ul>
            {Object.entries(counts).map(([type, count]) => (
              <li key={type}>
                {type}: {count}
              </li>
            ))}
          </ul>
        </>
      )}

      {Array.isArray(trend) && trend.length > 0 && (
        <>
          <h3>Recent Trend</h3>
          <ul>
            {trend.map((t, idx) => (
              <li key={idx}>
                {t.date}: {t.count}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
