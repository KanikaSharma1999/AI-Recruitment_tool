import { useState } from 'react';

const DIMS = [
  {
    key: 'skill_score',
    label: 'Skill Match (40%)',
    desc: 'Exact, semantic, and partial matches on required JD skills',
  },
  {
    key: 'experience_score',
    label: 'Experience (25%)',
    desc: 'Years of relevant professional experience vs. role requirement',
  },
  {
    key: 'semantic_score',
    label: 'Semantic Match (15%)',
    desc: 'AI-assessed contextual relevance of resume text to the job description',
  },
  {
    key: 'projects_score',
    label: 'Projects (10%)',
    desc: 'Relevance, complexity, and number of projects matching JD requirements',
  },
  {
    key: 'certification_score',
    label: 'Certifications (5%)',
    desc: 'Relevant professional credentials and training',
  },
  {
    key: 'resume_quality',
    label: 'Resume Quality (5%)',
    desc: 'Contact info availability, completeness, extraction confidence, and text density',
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

  const overallScore = Math.round(candidate.ai_match_score !== undefined && candidate.ai_match_score !== null ? candidate.ai_match_score : candidate.score || 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="dimension-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {dims.map(d => {
          const c = getColor(d.score);
          return (
            <div
              key={d.key}
              className="dimension-item"
              style={{ position: 'relative', cursor: 'default', padding: '12px 14px', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--bg-secondary)' }}
              onMouseEnter={() => setTooltip(d.key)}
              onMouseLeave={() => setTooltip(null)}
            >
              <div className="dimension-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span className="dimension-label" style={{ fontSize: 13, fontWeight: 700 }}>{d.label}</span>
                <span className="dimension-score" style={{ color: c.text, fontWeight: 800, fontSize: 14 }}>
                  {d.score}%
                </span>
              </div>
              <div className="score-bar-track" style={{ height: 6, background: '#e2e8f0', borderRadius: 999, overflow: 'hidden' }}>
                <div className={`score-bar-fill ${c.fill}`} style={{ width: `${d.score}%`, height: '100%', transition: 'width 0.5s ease-in-out' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                <span style={{
                  fontSize: 10, fontWeight: 700, color: c.text,
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
      </div>

      {/* Overall composite score block */}
      <div className="dimension-item" style={{ borderColor: '#6366f1', background: 'linear-gradient(135deg, #eef2ff, #f5f3ff)', border: '1px solid #c7d2fe', borderRadius: 12, padding: 16 }}>
        <div className="dimension-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 15 }}>🎯</span>
            <span className="dimension-label" style={{ fontWeight: 700, fontSize: 14, color: '#4f46e5' }}>Overall Match Score</span>
          </div>
          <span className="dimension-score" style={{ color: '#4f46e5', fontSize: 22, fontWeight: 900 }}>
            {overallScore}%
          </span>
        </div>
        <div className="score-bar-track" style={{ height: 8, background: '#e2e8f0', borderRadius: 999, overflow: 'hidden' }}>
          <div
            className="score-bar-fill"
            style={{
              width: `${overallScore}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #4f46e5, #818cf8)',
              transition: 'width 0.5s ease-in-out'
            }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          <span style={{ fontSize: 11, color: '#4f46e5', fontWeight: 600 }}>
            40% skill · 25% experience · 15% semantic · 10% project · 5% cert · 5% quality
          </span>
        </div>
      </div>

      {/* Risk flags */}
      {candidate.risk_flags?.length > 0 && (
        <div style={{ marginTop: 6, padding: 14, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: '#b45309', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>
            ⚠️ Penalties Applied
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {candidate.risk_flags.map((flag, i) => (
              <div key={i} className="risk-flag" style={{ fontSize: 12, color: '#78350f', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span>•</span> {flag}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
