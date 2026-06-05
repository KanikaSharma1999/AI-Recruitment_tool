export default function ProfileDonut({ score, breakdown }) {
  const size = 160, r = 58, cx = 80, cy = 80;
  const circ = 2 * Math.PI * r;
  const segments = [
    { key: 'skill_score',      label: 'Skills Match',   color: '#6366f1' },
    { key: 'experience_score', label: 'Experience',      color: '#10b981' },
    { key: 'semantic_score',   label: 'Semantic',        color: '#f59e0b' },
    { key: 'quality_score',    label: 'Resume Quality',  color: '#ef4444' },
    { key: 'cert_score',       label: 'Certifications',  color: '#8b5cf6' },
  ];
  const vals = segments.map(s => Math.max(0, parseFloat(breakdown?.[s.key] || 0)));
  const total = vals.reduce((a, b) => a + b, 0) || 1;
  let offset = 0;
  return (
    <div style={{ display: 'flex', gap: 24, alignItems: 'center' }}>
      <svg width={size} height={size} style={{ flexShrink: 0 }}>
        {vals.map((v, i) => {
          const frac = v / total;
          const dash = frac * circ;
          const gap = circ - dash;
          const el = (
            <circle key={i} cx={cx} cy={cy} r={r}
              fill="none" stroke={segments[i].color} strokeWidth={18}
              strokeDasharray={`${dash} ${gap}`}
              strokeDashoffset={-offset * circ / total + circ * 0.25}
              style={{ transition: 'stroke-dasharray 0.6s ease' }} />
          );
          offset += v;
          return el;
        })}
        <circle cx={cx} cy={cy} r={r - 10} fill="white" />
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize="22" fontWeight="800" fill="#0f172a">{Math.round(score)}%</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="10" fill="#64748b">Total Score</text>
      </svg>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {segments.map((s, i) => {
          const v = Math.round(vals[i]);
          return (
            <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
              <span style={{ fontSize: 11.5, color: '#475569', flex: 1 }}>{s.label}</span>
              <span style={{ fontSize: 11.5, fontWeight: 700, color: '#1e293b', width: 30, textAlign: 'right' }}>{v}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
