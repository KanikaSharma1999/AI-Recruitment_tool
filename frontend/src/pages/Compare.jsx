import { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import API from '../api/client';
import { MdWorkOutline, MdPerson, MdCheckCircle, MdCompare, MdAutoAwesome, MdWarning, MdStar } from 'react-icons/md';

const PALETTE = ['#6366f1', '#10b981', '#f59e0b'];

// ── Helpers ───────────────────────────────────────────────────────────────────
const val = (v, fallback = 0) => (typeof v === 'number' ? v : fallback);

const MiniBar = ({ value, color, max = 100 }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <div style={{ flex: 1, height: 6, background: '#e5e7eb', borderRadius: 999, overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${Math.min(val(value), max)}%`, background: color, borderRadius: 999, transition: 'width 0.8s' }} />
    </div>
    <span style={{ fontSize: 12, fontWeight: 600, minWidth: 36, textAlign: 'right', color }}>{Math.round(val(value))}%</span>
  </div>
);

const Delta = ({ a, b }) => {
  const d = Math.round((val(a) - val(b)));
  if (d === 0) return <span style={{ color: '#9ca3af', fontSize: 11 }}>—</span>;
  return <span style={{ fontSize: 11, fontWeight: 600, color: d > 0 ? '#059669' : '#dc2626' }}>{d > 0 ? `+${d}` : d}</span>;
};

const Chip = ({ label, color = '#6366f1', bg = '#ede9fe' }) => (
  <span style={{ padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 600, background: bg, color, marginRight: 4, marginBottom: 4, display: 'inline-block' }}>{label}</span>
);

const RiskBadge = ({ risk }) => {
  const r = (risk || '').toLowerCase();
  if (r.includes('high') || r.includes('flagged')) return <Chip label="High Risk" color="#dc2626" bg="#fee2e2" />;
  if (r.includes('medium') || r.includes('moderate')) return <Chip label="Medium" color="#d97706" bg="#fef3c7" />;
  return <Chip label="Low Risk" color="#059669" bg="#d1fae5" />;
};

const RecBadge = ({ rec }) => {
  const map = { 'Strong Hire': ['#065f46', '#d1fae5'], 'Hire': ['#1e40af', '#dbeafe'], 'Hold': ['#92400e', '#fef3c7'], 'Reject': ['#991b1b', '#fee2e2'] };
  const [c, bg] = map[rec] || ['#475569', '#f1f5f9'];
  return rec ? <Chip label={rec} color={c} bg={bg} /> : <span style={{ color: '#94a3b8', fontSize: 12 }}>Not ranked</span>;
};

// ── Step 1: Job selector ──────────────────────────────────────────────────────
function JobSelector({ jobs, onSelect }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {jobs.length === 0 && <div style={{ textAlign: 'center', color: '#94a3b8', padding: 40 }}>No jobs found. Create a job posting first.</div>}
      {jobs.map(j => (
        <button key={j.id} onClick={() => onSelect(j)}
          style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '16px 20px', border: '1.5px solid #e2e8f0', borderRadius: 14, background: '#fff', cursor: 'pointer', textAlign: 'left', transition: 'all 0.18s' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.background = '#fafafe'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = '#e2e8f0'; e.currentTarget.style.background = '#fff'; }}
        >
          <div style={{ width: 44, height: 44, borderRadius: 12, background: '#ede9fe', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <MdWorkOutline style={{ color: '#6366f1', fontSize: 22 }} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: '#1e293b' }}>{j.title}</div>
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{j.candidate_count ?? ''} candidates · {j.department || 'General'}</div>
          </div>
          <div style={{ fontSize: 12, color: '#6366f1', fontWeight: 600 }}>Select →</div>
        </button>
      ))}
    </div>
  );
}

// ── Step 2: Candidate card selector ──────────────────────────────────────────
function CandidateSelector({ candidates, selected, onToggle }) {
  const recColor = { 'Strong Hire': '#059669', 'Hire': '#2563eb', 'Hold': '#d97706', 'Reject': '#dc2626', 'Awaiting JD': '#64748b' };
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
      {candidates.length === 0 && (
        <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: 40 }}>No ranked candidates in this pipeline. Run AI ranking first.</div>
      )}
      {candidates.map((c, i) => {
        const isSelected = selected.includes(c.id);
        const rank = selected.indexOf(c.id);
        const rec = c.ai_verdict;
        return (
          <div key={c.id} onClick={() => onToggle(c.id)}
            style={{ padding: 16, border: `2px solid ${isSelected ? PALETTE[rank] : '#e2e8f0'}`, borderRadius: 14, cursor: 'pointer', background: isSelected ? '#fafafe' : '#fff', position: 'relative', transition: 'all 0.18s', boxShadow: isSelected ? `0 0 0 3px ${PALETTE[rank]}22` : 'none' }}>
            {isSelected && (
              <div style={{ position: 'absolute', top: 10, right: 10, width: 22, height: 22, borderRadius: '50%', background: PALETTE[rank], display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <MdCheckCircle style={{ color: '#fff', fontSize: 14 }} />
              </div>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: isSelected ? PALETTE[rank] : '#e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'center', color: isSelected ? '#fff' : '#64748b', fontWeight: 600, fontSize: 15, flexShrink: 0 }}>
                {(c.name || '?')[0].toUpperCase()}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#1e293b' }}>{c.name}</div>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>{c.experience_years || 0}y exp</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 22, fontWeight: 600, color: isSelected ? PALETTE[rank] : '#475569' }}>
                {(c.ai_match_score !== undefined && c.ai_match_score !== null) ? `${Math.round(c.ai_match_score)}%` : 'Awaiting JD'}
              </span>
              {rec && <span style={{ fontSize: 10, fontWeight: 600, color: recColor[rec] || '#64748b', background: '#f1f5f9', padding: '2px 7px', borderRadius: 999 }}>{rec}</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Step 3: Enterprise comparison table ──────────────────────────────────────
function CompareTable({ candidates }) {
  const rows = [
    { label: 'AI Match Score', render: (c, i) => <MiniBar value={c.ai_match_score !== undefined && c.ai_match_score !== null ? c.ai_match_score : c.score} color={PALETTE[i]} /> },
    { label: 'Experience', render: c => <span style={{ fontWeight: 600, fontSize: 13 }}>{val(c.experience_years, 0).toFixed(1)} years</span> },
    { label: 'Skills Match %', render: (c, i) => <MiniBar value={c.technical_fit} color={PALETTE[i]} /> },
    { label: 'Matched Skills', render: c => <div>{(c.matched_skills || c.skills || []).slice(0, 5).map(s => <Chip key={s} label={s} color="#059669" bg="#d1fae5" />)}{!(c.matched_skills || c.skills || []).length && <span style={{ color: '#94a3b8', fontSize: 12 }}>None</span>}</div> },
    { label: 'Missing Skills', render: c => <div>{(c.missing_skills || []).slice(0, 5).map(s => <Chip key={s} label={s} color="#dc2626" bg="#fee2e2" />)}{!c.missing_skills?.length && <Chip label="Full Match" color="#059669" bg="#d1fae5" />}</div> },
    { label: 'AI Recommendation', render: c => <RecBadge rec={c.ai_verdict} /> },
    { label: 'Resume Summary', render: c => <div style={{ fontSize: 12, color: '#475569', lineHeight: 1.5, maxHeight: 80, overflow: 'hidden' }}>{c.hiring_summary?.summary || c.ai_analysis?.executive_summary || 'No summary available'}</div> },
    { label: 'Strengths', render: c => <div>{(c.hiring_summary?.strengths || []).slice(0, 3).map((s, i) => <div key={i} style={{ fontSize: 12, color: '#059669', marginBottom: 2 }}>• {s}</div>)}{!c.hiring_summary?.strengths?.length && <span style={{ color: '#94a3b8', fontSize: 12 }}>—</span>}</div> },
    { label: 'Weaknesses', render: c => <div>{(c.hiring_summary?.weaknesses || []).slice(0, 3).map((w, i) => <div key={i} style={{ fontSize: 12, color: '#dc2626', marginBottom: 2 }}>• {w}</div>)}{!c.hiring_summary?.weaknesses?.length && <span style={{ color: '#94a3b8', fontSize: 12 }}>—</span>}</div> },
    { label: 'Communication', render: (c, i) => <MiniBar value={c.ai_analysis?.communication_score || c.communication_score} color={PALETTE[i]} /> },
    { label: 'Attention Score', render: (c, i) => <MiniBar value={c.ai_analysis?.attention_score} color={PALETTE[i]} /> },
    { label: 'Integrity Risk', render: c => <RiskBadge risk={c.ai_analysis?.cheating_risk || c.ai_analysis?.integrity_risk} /> },
    { label: 'Education', render: c => <div style={{ fontSize: 12, color: '#475569' }}>{(c.education || []).slice(0, 2).join(' · ') || '—'}</div> },
    { label: 'Certifications', render: c => <div>{(c.certifications || []).slice(0, 3).map(s => <Chip key={s} label={s} color="#7c3aed" bg="#ede9fe" />)}{!c.certifications?.length && <span style={{ color: '#94a3b8', fontSize: 12 }}>None listed</span>}</div> },
    { label: 'Interview Status', render: c => <span style={{ fontSize: 12, fontWeight: 600 }}>{(c.interview?.status || c.status || '—').replace(/_/g, ' ')}</span> },
  ];

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
            <th style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, color: '#64748b', width: 180, textTransform: 'uppercase', letterSpacing: '0.5px' }}>METRIC</th>
            {candidates.map((c, i) => (
              <th key={c.id} style={{ padding: '12px 16px', textAlign: 'left', fontWeight: 600, fontSize: 13, color: PALETTE[i], borderLeft: `3px solid ${PALETTE[i]}` }}>
                <div>{c.name}</div>
                <div style={{ fontSize: 11, color: '#94a3b8', fontWeight: 500 }}>{val(c.experience_years, 0).toFixed(0)} yrs exp</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} style={{ borderBottom: '1px solid #f1f5f9', background: ri % 2 === 0 ? '#fff' : '#fafafa' }}>
              <td style={{ padding: '12px 16px', fontWeight: 600, fontSize: 12, color: '#475569', whiteSpace: 'nowrap' }}>{row.label}</td>
              {candidates.map((c, ci) => (
                <td key={c.id} style={{ padding: '12px 16px', verticalAlign: 'top', borderLeft: `1px solid ${PALETTE[ci]}22` }}>
                  {row.render(c, ci)}
                  {ci > 0 && row.label.includes('%') && <div style={{ marginTop: 4 }}><Delta a={candidates[ci][row.key]} b={candidates[0][row.key]} /></div>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Recruiter Insights Panel ──────────────────────────────────────────────────
function RecruiterInsights({ candidates, aiInsights, loadingInsights }) {
  if (candidates.length < 2) return null;

  const best = (fn) => candidates.reduce((a, b) => fn(a) >= fn(b) ? a : b);
  const lowest = (fn) => candidates.reduce((a, b) => fn(a) <= fn(b) ? a : b);

  const insights = [
    { icon: '', label: 'Best Technical Fit', winner: best(c => val(c.technical_fit)), metric: c => `${Math.round(val(c.technical_fit))}% fit` },
    { icon: '', label: 'Best Communication', winner: best(c => val(c.ai_analysis?.communication_score || c.communication_score)), metric: c => `${Math.round(val(c.ai_analysis?.communication_score || c.communication_score))}%` },
    { icon: '', label: 'Lowest Risk', winner: lowest(c => { const r = (c.ai_analysis?.cheating_risk || '').toLowerCase(); return r.includes('high') ? 2 : r.includes('medium') ? 1 : 0; }), metric: () => 'Low risk' },
    { icon: '', label: 'Most Experienced', winner: best(c => val(c.experience_years)), metric: c => `${val(c.experience_years, 0).toFixed(1)} yrs` },
    { icon: '', label: 'Best Overall Match', winner: best(c => val(c.ai_match_score !== undefined && c.ai_match_score !== null ? c.ai_match_score : c.score)), metric: c => `${Math.round(val(c.ai_match_score !== undefined && c.ai_match_score !== null ? c.ai_match_score : c.score))}% match` },
  ];

  const overallBest = best(c => val(c.ai_match_score !== undefined && c.ai_match_score !== null ? c.ai_match_score : c.score));
  const secondBest = candidates.filter(c => c.id !== overallBest.id).sort((a, b) => val(b.ai_match_score !== undefined && b.ai_match_score !== null ? b.ai_match_score : b.score) - val(a.ai_match_score !== undefined && a.ai_match_score !== null ? a.ai_match_score : a.score))[0];

  return (
    <div style={{ background: 'linear-gradient(135deg, #1e293b, #0f172a)', borderRadius: 16, padding: 28, marginBottom: 24, color: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 22 }}>
        <MdAutoAwesome style={{ color: '#fbbf24', fontSize: 22 }} />
        <div style={{ fontWeight: 600, fontSize: 16 }}>AI Recruiter Insights</div>
        <div style={{ marginLeft: 'auto', fontSize: 11, color: '#94a3b8', background: '#1e293b', padding: '3px 10px', borderRadius: 999, border: '1px solid #334155' }}>Powered by AI</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14, marginBottom: 24 }}>
        {insights.map((ins, i) => {
          const winnerIdx = candidates.findIndex(c => c.id === ins.winner?.id);
          return (
            <div key={i} style={{ background: '#1e293b', borderRadius: 12, padding: '14px 16px', border: `1px solid ${PALETTE[winnerIdx] || '#334155'}44` }}>
              <div style={{ fontSize: 18, marginBottom: 6 }}>{ins.icon}</div>
              <div style={{ fontSize: 10, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>{ins.label}</div>
              <div style={{ fontWeight: 600, fontSize: 14, color: PALETTE[winnerIdx] || '#fff' }}>{ins.winner?.name || '—'}</div>
              <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{ins.winner ? ins.metric(ins.winner) : ''}</div>
            </div>
          );
        })}
      </div>

      <div style={{ background: '#0f172a', borderRadius: 12, padding: 18, borderLeft: '3px solid #6366f1' }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: '#6366f1', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          <MdStar style={{ verticalAlign: 'middle', marginRight: 4 }} />FINAL AI RECOMMENDATION
        </div>
        <div style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.7, margin: 0, minHeight: 60, whiteSpace: 'pre-wrap' }}>
          {aiInsights ? (
            aiInsights
          ) : loadingInsights ? (
            <span style={{ color: '#94a3b8' }}>Analyzing candidates and generating recommendation...</span>
          ) : (
            <span style={{ color: '#94a3b8' }}>Recommendation unavailable.</span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────
export default function Compare() {
  const [step, setStep] = useState(1);
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [jobCandidates, setJobCandidates] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [compareData, setCompareData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [error, setError] = useState('');
  const [aiInsights, setAiInsights] = useState('');
  const [loadingInsights, setLoadingInsights] = useState(false);

  useEffect(() => {
    API.get('/jobs/list').then(r => setJobs(r.data || [])).catch(() => {});
  }, []);

  const handleSelectJob = async (job) => {
    setSelectedJob(job);
    setSelectedIds([]);
    setCompareData([]);
    setStep(2);
    setLoadingCandidates(true);
    try {
      const res = await API.get(`/candidates/list?job_id=${job.id}`);
      const sorted = [...(res.data || [])].sort((a, b) => {
        const scoreA = a.ai_match_score !== undefined && a.ai_match_score !== null ? a.ai_match_score : (a.score || 0);
        const scoreB = b.ai_match_score !== undefined && b.ai_match_score !== null ? b.ai_match_score : (b.score || 0);
        return scoreB - scoreA;
      });
      setJobCandidates(sorted);
    } catch {
      setError('Failed to load candidates for this role.');
    } finally {
      setLoadingCandidates(false);
    }
  };

  const toggleCandidate = (id) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= 3) return prev; // max 3
      return [...prev, id];
    });
    setCompareData([]);
  };

  const handleCompare = async () => {
    if (selectedIds.length < 2) { setError('Select at least 2 candidates.'); return; }
    setError(''); setLoading(true); setAiInsights('');
    try {
      const res = await API.get(`/candidates/compare?ids=${selectedIds.join(',')}`);
      setCompareData(res.data || []);
      setStep(3);
      
      setLoadingInsights(true);
      const token = localStorage.getItem('ats_token');
      const url = `${API.defaults.baseURL || import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_BACKEND_URL || ''}/candidates/compare-insights?ids=${selectedIds.join(',')}`;
      
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Insights failed');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        setAiInsights(prev => prev + decoder.decode(value, { stream: true }));
      }
    } catch (err) {
      console.error(err);
      if (!aiInsights) setAiInsights('Error generating AI recommendation.');
      // Keep compareData but show error for insights
      if (!compareData.length) setError('Comparison failed. Please try again.');
    } finally { 
      setLoading(false); 
      setLoadingInsights(false);
    }
  };

  const StepBadge = ({ n, label, active, done }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 13, background: done ? '#10b981' : active ? '#6366f1' : '#e2e8f0', color: done || active ? '#fff' : '#94a3b8' }}>
        {done ? '✓' : n}
      </div>
      <span style={{ fontSize: 13, fontWeight: active ? 600 : 500, color: active ? '#1e293b' : '#94a3b8' }}>{label}</span>
    </div>
  );

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Candidate Comparison" />
        <div className="page-body animate-fade">

          <div style={{ marginBottom: 24 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1e293b' }}>Enterprise Candidate Comparison</h1>
            <p style={{ color: '#64748b', fontSize: 13 }}>Job-scoped side-by-side intelligence — compare candidates from the same pipeline only.</p>
          </div>

          {/* Step indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 28, padding: '16px 24px', background: '#fff', borderRadius: 14, border: '1px solid #e2e8f0' }}>
            <StepBadge n={1} label="Select Job Role" active={step === 1} done={step > 1} />
            <div style={{ flex: 1, height: 2, background: step > 1 ? '#6366f1' : '#e2e8f0', borderRadius: 999 }} />
            <StepBadge n={2} label="Choose Candidates" active={step === 2} done={step > 2} />
            <div style={{ flex: 1, height: 2, background: step > 2 ? '#6366f1' : '#e2e8f0', borderRadius: 999 }} />
            <StepBadge n={3} label="Compare & Analyse" active={step === 3} done={false} />
          </div>

          {/* STEP 1 */}
          {step === 1 && (
            <div style={{ background: '#fff', borderRadius: 16, padding: 24, border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 600, fontSize: 15, color: '#1e293b', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <MdWorkOutline style={{ color: '#6366f1' }} /> Select a Job Role to Compare Candidates Within
              </div>
              <JobSelector jobs={jobs} onSelect={handleSelectJob} />
            </div>
          )}

          {/* STEP 2 */}
          {step === 2 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <div>
                  <button onClick={() => { setStep(1); setSelectedJob(null); }} style={{ fontSize: 12, color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, marginBottom: 6 }}>← Change Role</button>
                  <div style={{ fontWeight: 600, fontSize: 16, color: '#1e293b', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <MdPerson style={{ color: '#6366f1' }} /> {selectedJob?.title}
                    <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 400 }}>— select 2 or 3 candidates to compare</span>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 13, color: '#64748b' }}>{selectedIds.length}/3 selected</span>
                  <button onClick={handleCompare} disabled={selectedIds.length < 2 || loading}
                    style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 22px', background: selectedIds.length >= 2 ? '#6366f1' : '#e2e8f0', color: selectedIds.length >= 2 ? '#fff' : '#94a3b8', border: 'none', borderRadius: 10, fontWeight: 600, fontSize: 13, cursor: selectedIds.length >= 2 ? 'pointer' : 'not-allowed' }}>
                    <MdCompare /> {loading ? 'Loading...' : 'Compare Now'}
                  </button>
                </div>
              </div>

              {loadingCandidates ? (
                <div style={{ textAlign: 'center', padding: 60, color: '#94a3b8' }}>Loading candidates...</div>
              ) : (
                <CandidateSelector candidates={jobCandidates} selected={selectedIds} onToggle={toggleCandidate} />
              )}
              {error && <div style={{ marginTop: 12, color: '#dc2626', fontSize: 13 }}>{error}</div>}
            </div>
          )}

          {/* STEP 3 */}
          {step === 3 && compareData.length >= 2 && (
            <div className="animate-fade">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                <button onClick={() => setStep(2)} style={{ fontSize: 12, color: '#6366f1', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>← Back to Selection</button>
                <span style={{ color: '#e2e8f0' }}>|</span>
                <span style={{ fontSize: 13, color: '#475569', fontWeight: 600 }}>{selectedJob?.title} — Comparing {compareData.length} candidates</span>
              </div>

              <RecruiterInsights candidates={compareData} aiInsights={aiInsights} loadingInsights={loadingInsights} />

              <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                <div style={{ padding: '18px 24px', borderBottom: '1px solid #f1f5f9', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <MdCompare style={{ color: '#6366f1', fontSize: 20 }} />
                  <span style={{ fontWeight: 600, fontSize: 15, color: '#1e293b' }}>Side-by-Side Enterprise Analysis</span>
                </div>
                <CompareTable candidates={compareData} />
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
