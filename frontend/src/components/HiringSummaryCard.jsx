const REC_CONFIG = {
  'Strong Hire': { bg: '#d1fae5', border: '#6ee7b7', text: '#065f46', icon: '', accent: '#059669' },
  'Hire':        { bg: '#dbeafe', border: '#93c5fd', text: '#1e40af', icon: '', accent: '#2563eb' },
  'Hold':        { bg: '#fef3c7', border: '#fcd34d', text: '#92400e', icon: '', accent: '#d97706' },
  'Reject':      { bg: '#fee2e2', border: '#fca5a5', text: '#991b1b', icon: '',  accent: '#dc2626' },
};

const CONF_CONFIG = {
  'High':   { color: '#059669', label: 'High Confidence' },
  'Medium': { color: '#d97706', label: 'Medium Confidence' },
  'Low':    { color: '#dc2626', label: 'Low Confidence' },
};

export default function HiringSummaryCard({ candidate }) {
  const summary = candidate?.hiring_summary;
  if (!summary) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '28px 24px', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: 28, marginBottom: 8, color: 'var(--text-muted)' }}></div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>AI summary not yet generated</div>
        <div style={{ fontSize: 12, marginTop: 4 }}>Run ranking to generate hiring intelligence</div>
      </div>
    );
  }

  const rec = summary.recommendation || 'Hold';
  const conf = summary.confidence || 'Medium';
  const cfg = REC_CONFIG[rec] || REC_CONFIG['Hold'];
  const confCfg = CONF_CONFIG[conf] || CONF_CONFIG['Medium'];

  return (
    <div className="hiring-summary-card" style={{ borderColor: cfg.border }}>
      {/* Header */}
      <div
        className="hiring-summary-header"
        style={{ background: cfg.bg, borderBottom: `1px solid ${cfg.border}` }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: cfg.text }}>{cfg.icon}</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 800, color: cfg.text }}>{rec}</div>
            <div style={{ fontSize: 11, color: cfg.accent, fontWeight: 600 }}>AI Hiring Recommendation</div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 8, height: 8, borderRadius: '50%',
              background: confCfg.color,
              boxShadow: `0 0 6px ${confCfg.color}`,
            }}
          />
          <span style={{ fontSize: 11.5, fontWeight: 600, color: confCfg.color }}>
            {confCfg.label}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="hiring-summary-body" style={{ background: '#fff' }}>
        {/* Narrative */}
        {summary.narrative && (
          <p className="summary-narrative">{summary.narrative}</p>
        )}

        {/* Strengths & Weaknesses */}
        {(summary.strengths?.length > 0 || summary.weaknesses?.length > 0) && (
          <div className="summary-cols">
            {/* Strengths */}
            <div>
              <div className="summary-col-title" style={{ color: '#059669' }}>
                ✓ Strengths
              </div>
              {(summary.strengths || []).map((s, i) => (
                <div key={i} className="summary-point">
                  <span style={{ color: '#059669', fontSize: 14, lineHeight: 1 }}>•</span>
                  {s}
                </div>
              ))}
            </div>

            {/* Weaknesses */}
            <div>
              <div className="summary-col-title" style={{ color: '#dc2626' }}>
                Concerns
              </div>
              {(summary.weaknesses || []).map((w, i) => (
                <div key={i} className="summary-point">
                  <span style={{ color: '#dc2626', fontSize: 14, lineHeight: 1 }}>•</span>
                  {w}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Generated timestamp */}
        {summary.generated_at && (
          <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)', borderTop: '1px solid #f3f4f6', paddingTop: 10 }}>
            AI analysis generated · {new Date(summary.generated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        )}
      </div>
    </div>
  );
}
