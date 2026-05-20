import { useState } from 'react';

const DIMS = [
  {
    key: 'technical_fit',
    label: 'Technical Fit',
    desc: 'Blend of exact skill matches, semantic similarity, and contextual JD alignment',
    icon: '⚙️',
  },
  {
    key: 'experience_relevance',
    label: 'Experience',
    desc: 'Years of relevant professional experience vs. role requirement',
    icon: '📅',
  },
  {
    key: 'resume_quality',
    label: 'Resume Quality',
    desc: 'Completeness: education, projects, certifications, and detail depth',
    icon: '📄',
  },
];

function getColor(score) {
  if (score >= 75) return { fill: 'score-fill-excellent', text: '#059669', bg: '#d1fae5' };
  if (score >= 55) return { fill: 'score-fill-good', text: '#2563eb', bg: '#dbeafe' };
  if (score >= 35) return { fill: 'score-fill-average', text: '#d97706', bg: '#fef3c7' };
  return { fill: 'score-fill-poor', text: '#dc2626', bg: '#fee2e2' };
}

function getLabel(score) {
  if (score >= 75) return 'Excellent';
  if (score >= 55) return 'Good';
  if (score >= 35) return 'Fair';
  return 'Low';
}

export default function ScoreDimensions({ candidate, compact = false }) {
  const [tooltip, setTooltip] = useState(null);

  if (!candidate) return null;

  const dims = DIMS.map(d => ({
    ...d,
    score: Math.round(candidate[d.key] || 0),
  }));

  if (compact) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {dims.map(d => {
          const c = getColor(d.score);
          return (
            <div key={d.key} className="score-bar-wrap">
              <div className="score-bar-label">
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{d.label}</span>
                <span className="score-bar-value" style={{ color: c.text }}>{d.score}%</span>
              </div>
              <div className="score-bar-track">
                <div className={`score-bar-fill ${c.fill}`} style={{ width: `${d.score}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      <div className="dimension-grid">
        {dims.map(d => {
          const c = getColor(d.score);
          return (
            <div
              key={d.key}
              className="dimension-item"
              style={{ position: 'relative', cursor: 'default' }}
              onMouseEnter={() => setTooltip(d.key)}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="dimension-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 15 }}>{d.icon}</span>
                  <span className="dimension-label">{d.label}</span>
                </div>
                <span
                  className="dimension-score"
                  style={{ color: c.text }}
                >
                  {d.score}%
                </span>
              </div>
              <div className="score-bar-track" style={{ height: 6 }}>
                <div className={`score-bar-fill ${c.fill}`} style={{ width: `${d.score}%` }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                <span style={{
                  fontSize: 11, fontWeight: 600, color: c.text,
                  background: c.bg, padding: '2px 7px', borderRadius: 999,
                }}>
                  {getLabel(d.score)}
                </span>
              </div>
              {tooltip === d.key && (
                <div style={{
                  position: 'absolute', bottom: 'calc(100% + 6px)', left: 0, right: 0,
                  background: '#1f2937', color: '#fff', fontSize: 11.5, lineHeight: 1.5,
                  padding: '8px 10px', borderRadius: 8, zIndex: 10,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
                }}>
                  {d.desc}
                </div>
              )}
            </div>
          );
        })}
        {/* Overall composite score */}
        {candidate.score !== undefined && (
          <div className="dimension-item" style={{ borderColor: '#6366f1', background: '#fafaff' }}>
            <div className="dimension-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 15 }}>🎯</span>
                <span className="dimension-label">Overall Match</span>
              </div>
              <span className="dimension-score" style={{ color: '#6366f1', fontSize: 20 }}>
                {Math.round(candidate.score)}%
              </span>
            </div>
            <div className="score-bar-track" style={{ height: 6 }}>
              <div
                className="score-bar-fill"
                style={{
                  width: `${candidate.score}%`,
                  background: 'linear-gradient(90deg, #6366f1, #a5b4fc)',
                }}
              />
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              60% skill · 30% experience · 10% semantic
            </span>
          </div>
        )}
      </div>

      {/* Risk flags */}
      {candidate.risk_flags?.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9a3412', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>
            Risk Flags
          </div>
          {candidate.risk_flags.map((flag, i) => (
            <div key={i} className="risk-flag">
              <span style={{ fontSize: 13 }}>⚠</span>
              {flag}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
