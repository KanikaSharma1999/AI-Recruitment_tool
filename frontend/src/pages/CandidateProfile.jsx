import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import StatusBadge from '../components/StatusBadge';
import InterviewModal from '../components/InterviewModal';
import InterviewMonitor from '../components/InterviewMonitor';
import ScoreDimensions from '../components/ScoreDimensions';
import HiringSummaryCard from '../components/HiringSummaryCard';
import InterviewPrepCard from '../components/InterviewPrepCard';
import InterviewInsightCard from '../components/InterviewInsightCard';
import API from '../api/client';
import toast from 'react-hot-toast';
import { MdArrowBack, MdCalendarToday, MdThumbUp, MdThumbDown, MdCheckCircle,
         MdSend, MdDelete, MdOpenInNew, MdInfoOutline, MdExpandMore, MdExpandLess, MdCompare } from 'react-icons/md';

// ── Score helpers ─────────────────────────────────────────────────────────────
const safeScore = (value) => {
  if (value === null || value === undefined || value === '') return 0;
  return Math.min(100, Math.max(0, Math.round(Number(value))));
};

const getColor = (score) => {
  if (score > 80) return '#22c55e';
  if (score > 50) return '#f59e0b';
  return '#ef4444';
};

// ── Resume Preview Component ──────────────────────────────────────────────────
const ResumePreview = ({ id, filename }) => {
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const url = `${API.defaults.baseURL}/candidates/${id}/resume`;

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ fontSize: 15, fontWeight: 700 }}>📄 Resume: {filename}</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button 
            className="btn btn-sm btn-outline"
            onClick={() => window.open(url, '_blank')}
          >
            <MdOpenInNew /> Open External
          </button>
          <a 
            href={url} 
            download 
            className="btn btn-sm btn-outline"
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <MdSend style={{ transform: 'rotate(90deg)' }} /> Download
          </a>
        </div>
      </div>

      <div style={{ 
        height: 500, background: 'var(--bg-secondary)', borderRadius: 12, 
        border: '1px solid var(--border)', overflow: 'hidden', position: 'relative',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        {loading && !error && (
          <div style={{ position: 'absolute', textAlign: 'center' }}>
            <div className="spinner" style={{ margin: '0 auto 10px' }} />
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Loading resume preview...</div>
          </div>
        )}

        {error ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <div style={{ fontSize: 40, marginBottom: 10 }}>⚠️</div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Resume File Not Found</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', maxWidth: 250 }}>
              The physical file might have been moved or deleted from the server.
            </div>
          </div>
        ) : (
          <iframe 
            src={`${url}#toolbar=0`} 
            style={{ width: '100%', height: '100%', border: 'none' }}
            onLoad={() => setLoading(false)}
            onError={() => setError(true)}
          />
        )}
      </div>
    </div>
  );
};

// ── Clean score bar (shows ONLY the actual score, no weight mixing) ────────────
const ScoreBar = ({ label, score, tooltip }) => {
  const s = safeScore(score);
  const [showTip, setShowTip] = useState(false);
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-label">
        <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
          {label}
          {tooltip && (
            <span
              style={{ position: 'relative', cursor: 'help' }}
              onMouseEnter={() => setShowTip(true)}
              onMouseLeave={() => setShowTip(false)}
            >
              <MdInfoOutline style={{ fontSize: 13, color: 'var(--text-secondary)', verticalAlign: 'middle' }} />
              {showTip && (
                <span style={{
                  position: 'absolute', left: 20, top: -4, zIndex: 10,
                  background: '#1e293b', color: '#fff', fontSize: 11,
                  padding: '4px 8px', borderRadius: 6, whiteSpace: 'nowrap', boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                }}>{tooltip}</span>
              )}
            </span>
          )}
        </span>
        <span style={{ fontWeight: 800, color: getColor(s), fontSize: 15 }}>{s}%</span>
      </div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${s}%`, backgroundColor: getColor(s),
          transition: 'width 0.6s cubic-bezier(0.4,0,0.2,1)' }} />
      </div>
    </div>
  );
};

// ── AI Match Score card ────────────────────────────────────────────────────────
const AIMatchScoreCard = ({ c }) => {
  const [showWeights, setShowWeights] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);

  const overall   = safeScore(c.score);
  const skillS    = safeScore(c.skill_score);
  const expS      = safeScore(c.experience_score);
  const semanticS = safeScore(c.semantic_score);
  const expl      = c.match_explanation || {};
  const breakdown = expl.score_breakdown || {};

  const ringColor = getColor(overall);

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16, fontSize: 15, fontWeight: 700 }}>🎯 AI Match Score</h3>

      {/* Overall score ring */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 20 }}>
        <div style={{
          width: 90, height: 90, borderRadius: '50%',
          background: `conic-gradient(${ringColor} ${overall * 3.6}deg, #e2e8f0 0deg)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          boxShadow: `0 0 0 6px ${ringColor}18`,
        }}>
          <div style={{
            width: 68, height: 68, borderRadius: '50%',
            background: 'var(--bg-primary)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ fontSize: 22, fontWeight: 900, color: ringColor, lineHeight: 1 }}>{overall}%</span>
            <span style={{ fontSize: 9, color: 'var(--text-secondary)', fontWeight: 600 }}>OVERALL</span>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
            Overall Match Score
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {expl.overall_verdict || (overall >= 80 ? '🟢 Excellent match' : overall >= 60 ? '🟡 Good match' : overall >= 40 ? '🟠 Partial match' : '🔴 Weak match')}
          </div>
        </div>
      </div>

      {/* Score breakdown — actual scores ONLY */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Score Breakdown
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ScoreBar label="Skill Match"      score={c.skill_score}
            tooltip="How well candidate's skills match the job requirements" />
          <ScoreBar label="Experience Match" score={c.experience_score}
            tooltip="Candidate's years of experience vs. required years" />
          <ScoreBar label="Semantic Match"   score={c.semantic_score}
            tooltip="AI-assessed contextual relevance of resume content to the job" />
        </div>
      </div>

      {/* Weights toggle — separated from scores */}
      <button
        onClick={() => setShowWeights(v => !v)}
        style={{
          background: 'var(--bg-secondary)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '6px 12px', fontSize: 12, cursor: 'pointer',
          color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4,
          width: '100%', justifyContent: 'space-between', marginBottom: 4,
        }}
      >
        <span>ℹ️ How is this score calculated?</span>
        {showWeights ? <MdExpandLess /> : <MdExpandMore />}
      </button>
      {showWeights && (
        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 8, padding: '12px 14px',
          marginBottom: 8, fontSize: 12, lineHeight: 1.8,
        }}>
          <div style={{ fontWeight: 700, marginBottom: 6, fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Weights Used</div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {[['Skills', 60, '#6366f1'], ['Experience', 30, '#f59e0b'], ['Semantic', 10, '#22c55e']].map(([label, w, color]) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 10, height: 10, borderRadius: 3, background: color }} />
                <span><b>{label}</b> → {w}%</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 8, fontFamily: 'monospace', fontSize: 11, color: '#6366f1',
            background: '#eef2ff', padding: '4px 8px', borderRadius: 4 }}>
            {breakdown.formula || '0.60 × skill + 0.30 × experience + 0.10 × semantic'}
          </div>
        </div>
      )}

      {/* Why this score — expandable explanation */}
      {Object.keys(expl).length > 0 && (
        <>
          <button
            onClick={() => setShowExplanation(v => !v)}
            style={{
              background: 'linear-gradient(135deg, #eff6ff, #f0fdf4)',
              border: '1px solid #bfdbfe', borderRadius: 8,
              padding: '6px 12px', fontSize: 12, cursor: 'pointer',
              color: '#1d4ed8', display: 'flex', alignItems: 'center', gap: 4,
              width: '100%', justifyContent: 'space-between', fontWeight: 600,
            }}
          >
            <span>🔍 Why this score? (Match Explanation)</span>
            {showExplanation ? <MdExpandLess /> : <MdExpandMore />}
          </button>
          {showExplanation && (
            <div style={{
              border: '1px solid #bfdbfe', borderRadius: 8, padding: 14,
              marginTop: 6, background: '#fafbff', fontSize: 13,
            }}>
              {expl.skills_summary && (
                <div style={{ marginBottom: 10, fontWeight: 600, color: '#1d4ed8' }}>
                  📊 {expl.skills_summary}
                </div>
              )}
              {expl.exact_matches?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#15803d', marginBottom: 4 }}>✔ Exact Skill Matches</div>
                  <div>{expl.exact_matches.map(s => <span key={s} style={{ display:'inline-block', background:'#f0fdf4', color:'#15803d', border:'1px solid #bbf7d0', borderRadius:20, fontSize:11, fontWeight:600, padding:'2px 8px', margin:'2px 3px 2px 0' }}>{s}</span>)}</div>
                </div>
              )}
              {expl.semantic_matches?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#7c3aed', marginBottom: 4 }}>≈ Semantic Matches (AI-detected variants)</div>
                  <div>{expl.semantic_matches.map(s => <span key={s} style={{ display:'inline-block', background:'#f5f3ff', color:'#7c3aed', border:'1px solid #ddd6fe', borderRadius:20, fontSize:11, fontWeight:600, padding:'2px 8px', margin:'2px 3px 2px 0' }}>{s}</span>)}</div>
                </div>
              )}
              {expl.partial_matches?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#d97706', marginBottom: 4 }}>~ Partial Matches (fuzzy)</div>
                  <div>{expl.partial_matches.map(s => <span key={s} style={{ display:'inline-block', background:'#fffbeb', color:'#d97706', border:'1px solid #fde68a', borderRadius:20, fontSize:11, fontWeight:600, padding:'2px 8px', margin:'2px 3px 2px 0' }}>{s}</span>)}</div>
                </div>
              )}
              {expl.missing_skills?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', marginBottom: 4 }}>⚠ Missing Skills</div>
                  <div>{expl.missing_skills.map(s => <span key={s} style={{ display:'inline-block', background:'#fef2f2', color:'#dc2626', border:'1px solid #fecaca', borderRadius:20, fontSize:11, fontWeight:600, padding:'2px 8px', margin:'2px 3px 2px 0' }}>{s}</span>)}</div>
                </div>
              )}
              {expl.experience_verdict && (
                <div style={{ marginBottom: 8, padding: '6px 10px', background: '#f8fafc', borderRadius: 6, fontSize: 12 }}>
                  🗓 {expl.experience_verdict}
                </div>
              )}
              {expl.bonus_skills?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#0891b2', marginBottom: 4 }}>⭐ Bonus Skills (beyond requirements)</div>
                  <div>{expl.bonus_skills.map(s => <span key={s} style={{ display:'inline-block', background:'#ecfeff', color:'#0891b2', border:'1px solid #a5f3fc', borderRadius:20, fontSize:11, fontWeight:600, padding:'2px 8px', margin:'2px 3px 2px 0' }}>{s}</span>)}</div>
                </div>
              )}
              {expl.certifications?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#0f766e', marginBottom: 4 }}>🎓 Certifications</div>
                  <div style={{ fontSize: 12, color: '#0f766e' }}>{expl.certifications.join(' · ')}</div>
                </div>
              )}
              {expl.projects?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#7c3aed', marginBottom: 4 }}>📁 Detected Projects</div>
                  <div style={{ fontSize: 12 }}>{expl.projects.join(' · ')}</div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ── Skill chip variants ───────────────────────────────────────────────────────
const SkillChip = ({ skill, variant }) => {
  const styles = {
    required: { background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' },
    matched:  { background: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0' },
    missing:  { background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' },
    neutral:  { background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border)' },
  };
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: 20,
      fontSize: 12,
      fontWeight: 600,
      margin: '3px 4px 3px 0',
      ...styles[variant || 'neutral'],
    }}>
      {skill}
    </span>
  );
};

// ── Skill section with header and empty-state ─────────────────────────────────
const SkillSection = ({ icon, title, titleColor, skills, variant, emptyText }) => {
  if (!skills || skills.length === 0) {
    if (!emptyText) return null;
    return (
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: titleColor, marginBottom: 6 }}>
          {icon} {title}
        </div>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{emptyText}</span>
      </div>
    );
  }
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: titleColor, marginBottom: 6 }}>
        {icon} {title} <span style={{ fontWeight: 400 }}>({skills.length})</span>
      </div>
      <div>
        {skills.map(s => <SkillChip key={s} skill={s} variant={variant} />)}
      </div>
    </div>
  );
};

// ── AI Interview feedback card ────────────────────────────────────────────────
const AiFeedbackCard = ({ candidate }) => {
  const feedback = candidate.ai_analysis;
  if (!feedback) return (
    <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
      AI Interview Analysis will be generated automatically after the interview ends.
    </p>
  );

  const riskColor = {
    High:   '#ef4444',
    Medium: '#f59e0b',
    Low:    '#22c55e',
  }[feedback.cheating_risk] || 'var(--text-primary)';

  const recColor = feedback.recommendation?.toLowerCase().includes('hire')
    ? '#22c55e'
    : feedback.recommendation?.toLowerCase().includes('reject')
    ? '#ef4444'
    : '#f59e0b';

  const metrics = feedback.metrics || {};
  const explanation = feedback.explanation_details || {};

  const MetricItem = ({ label, value, subtext }) => (
    <div style={{ padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
        <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-primary)' }}>{value}</span>
      </div>
      {subtext && <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{subtext}</div>}
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      {/* Overview Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 10 }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 700, marginBottom: 4 }}>COMMUNICATION</div>
          <div style={{ fontSize: 18, fontWeight: 900, color: '#6366f1' }}>{feedback.communication}</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{metrics.comm_score}% Performance</div>
        </div>
        <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 10 }}>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 700, marginBottom: 4 }}>CONFIDENCE</div>
          <div style={{ fontSize: 18, fontWeight: 900, color: '#f59e0b' }}>{feedback.confidence}</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{metrics.conf_score}% Gaze Stability</div>
        </div>
      </div>

      <MetricItem 
        label="Speaking Ratio" 
        value={`${metrics.speaking_ratio}%`} 
        subtext={explanation.communication} 
      />
      <MetricItem 
        label="Eye Contact" 
        value={`${metrics.eye_contact}%`} 
        subtext={explanation.confidence} 
      />
      <MetricItem 
        label="Cheating Risk" 
        value={feedback.cheating_risk} 
        valueColor={riskColor}
        subtext={explanation.security} 
      />

      {/* Reasoning & Recommendation */}
      <div style={{ marginTop: 16, padding: 16, borderRadius: 12, 
                    background: feedback.recommendation?.toLowerCase().includes('hire') ? '#f0fdf4' : '#fef2f2',
                    border: `1px solid ${recColor}40` }}>
        <div style={{ marginBottom: 10 }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>Final Verdict: </span>
          <span style={{ fontWeight: 900, fontSize: 16, color: recColor }}>{feedback.recommendation}</span>
        </div>
        <div style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-primary)', fontStyle: 'italic' }}>
          " {feedback.reasoning} "
        </div>
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export default function CandidateProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState(null);
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [showInterview, setShowInterview] = useState(false);
  const [isInterviewing, setIsInterviewing] = useState(false);

  const fetchCandidate = () => {
    setLoading(true);
    API.get(`/candidates/${id}`)
      .then(r => {
        setC(r.data);
        // Debug scores in console
        console.log('[SCORE DEBUG]', {
          score:            r.data.score,
          semantic_score:   r.data.semantic_score,
          skill_score:      r.data.skill_score,
          experience_score: r.data.experience_score,
          job_required:     r.data.job_required_skills,
          matched:          r.data.matched_skills,
          missing:          r.data.missing_skills,
        });
      })
      .catch(() => toast.error('Candidate not found'))
      .finally(() => setLoading(false));
  };

  useEffect(fetchCandidate, [id]);

  const updateStatus = async (status) => {
    try {
      await API.put(`/candidates/${id}/status`, { status });
      toast.success(`Status → ${status}`);
      fetchCandidate();
    } catch { toast.error('Update failed'); }
  };

  const addNote = async (e) => {
    e.preventDefault();
    if (!note.trim()) return;
    setSavingNote(true);
    try {
      await API.post(`/candidates/${id}/notes`, { text: note });
      setNote('');
      toast.success('Note saved');
      fetchCandidate();
    } catch { toast.error('Failed to save note'); }
    finally { setSavingNote(false); }
  };

  const startInterview = () => {
    if (!c.interview?.meeting_link) {
      toast.error('No meeting link scheduled. Schedule an interview first.');
      return;
    }
    window.open(c.interview.meeting_link, '_blank');
    setIsInterviewing(true);
  };

  const endInterview = async () => {
    setIsInterviewing(false);
    toast.success('Interview ended. Generating AI Analysis...');
    try {
      await API.post('/interviews/analyze', { candidate_id: id });
      fetchCandidate();
    } catch {
      toast.error('Failed to generate AI Analysis');
    }
  };

  if (loading) return (
    <div className="layout">
      <Sidebar /><div className="main-content">
        <Navbar title="Candidate Profile" />
        <div style={{ padding: 60, textAlign: 'center' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
      </div>
    </div>
  );

  if (!c) return null;

  // Experience score color: red if 0, otherwise normal
  const expYears      = c.experience_years || 0;
  const expScoreSafe  = safeScore(c.experience_score);
  const expColor      = expYears <= 0 ? '#ef4444' : getColor(expScoreSafe);

  // Skill breakdown data
  const jdSkills      = c.job_required_skills || [];
  const matchedSkills = c.matched_skills      || [];
  const missingSkills = c.missing_skills      || [];
  const allSkills     = c.skills              || [];

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Candidate Profile" />
        <div className="page-body animate-fade">

          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
            <button className="btn btn-outline btn-sm" onClick={() => navigate(-1)}>
              <MdArrowBack /> Back
            </button>
            <div style={{ flex: 1 }}>
              <h1 style={{ fontSize: 22, fontWeight: 800 }}>{c.name}</h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{c.email} · {c.phone}</p>
            </div>
            <StatusBadge status={c.status} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>
            {/* ── LEFT COLUMN ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* AI Scoring — Multi-Dimensional */}
              <div className="card">
                <div className="card-title">🎯 AI Match Intelligence</div>
                <ScoreDimensions candidate={c} />
              </div>

              {/* Recruiter Matching Explanation & Enterprise Details */}
              {c.recruiter_explanation && (
                <div className="card" style={{ border: '1px solid #bfdbfe', background: 'linear-gradient(135deg, #eff6ff, #f8fafc)', borderRadius: 12, padding: 20 }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: 15, fontWeight: 800, color: '#1e40af', display: 'flex', alignItems: 'center', gap: 6 }}>
                    📋 Recruiter matching explanation
                  </h3>
                  <div style={{ color: '#1e3a8a', fontSize: 13.5, lineHeight: 1.6, whiteSpace: 'pre-line', marginBottom: 16 }}>
                    {c.recruiter_explanation}
                  </div>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, borderTop: '1px solid #dbeafe', paddingTop: 14 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#4b5563', textTransform: 'uppercase', marginBottom: 2 }}>AI Confidence</div>
                      <div style={{ fontSize: 13.5, fontWeight: 800, color: c.extraction_reliability === 'High' ? '#059669' : c.extraction_reliability === 'Medium' ? '#d97706' : '#dc2626' }}>
                        {c.confidence_score ? `${Math.round(c.confidence_score)}%` : '75%'} ({c.extraction_reliability || 'Medium'})
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#4b5563', textTransform: 'uppercase', marginBottom: 2 }}>Leadership Match</div>
                      <div style={{ fontSize: 13.5, fontWeight: 800, color: c.leadership_match === 'Yes' ? '#059669' : '#4b5563' }}>
                        {c.leadership_match || 'No'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#4b5563', textTransform: 'uppercase', marginBottom: 2 }}>Communication</div>
                      <div style={{ fontSize: 13.5, fontWeight: 800, color: c.communication_match === 'Verified' ? '#059669' : '#4b5563' }}>
                        {c.communication_match || 'Baseline'}
                      </div>
                    </div>
                  </div>

                  {c.ambiguity_detection && c.ambiguity_detection.length > 0 && (
                    <div style={{ marginTop: 14, fontSize: 11.5, color: '#6b7280', borderTop: '1px dashed #dbeafe', paddingTop: 10 }}>
                      <div style={{ fontWeight: 700, color: '#4b5563', marginBottom: 4 }}>⚠️ Ambiguity alerts:</div>
                      <ul style={{ margin: 0, paddingLeft: 16 }}>
                        {c.ambiguity_detection.map((amb, i) => (
                          <li key={i} style={{ marginBottom: 2 }}>{amb}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Hiring Summary */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>AI Hiring Summary</div>
                <HiringSummaryCard candidate={c} />
              </div>

              {/* ── SKILLS BREAKDOWN ── */}
              <div className="card">
                <h3 style={{ marginBottom: 14, fontSize: 15, fontWeight: 700 }}>🔬 Skills Breakdown</h3>

                {/* 1. Required Skills from JD */}
                <SkillSection
                  icon="📌"
                  title="Required Skills (JD)"
                  titleColor="#1d4ed8"
                  skills={jdSkills}
                  variant="required"
                  emptyText="No required skills extracted from JD. Re-create the job with a detailed description."
                />

                {/* 2. Matched Skills */}
                <SkillSection
                  icon="✅"
                  title="Matched Skills"
                  titleColor="#15803d"
                  skills={matchedSkills}
                  variant="matched"
                  emptyText={jdSkills.length > 0 ? 'No skills matched.' : null}
                />

                {/* 3. Missing Skills */}
                <SkillSection
                  icon="❌"
                  title="Missing Skills"
                  titleColor="#dc2626"
                  skills={missingSkills}
                  variant="missing"
                />

                {/* 4. All Extracted Skills from Resume */}
                {allSkills.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6 }}>
                      📋 All Extracted Resume Skills ({allSkills.length})
                    </div>
                    <div>
                      {allSkills.map(s => <SkillChip key={s} skill={s} variant="neutral" />)}
                    </div>
                  </div>
                )}
              </div>

              {/* 🤖 AI Resume Feedback — Redesigned for Structured Insights */}
              <div className="card" style={{ border: '1px solid var(--border)', background: 'linear-gradient(to bottom, #fff, #f8fafc)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
                  <span style={{ fontSize: 20 }}>🤖</span>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 800, color: 'var(--text-primary)' }}>AI Resume Evaluation</h3>
                </div>

                {c.feedback && typeof c.feedback === 'object' && Object.keys(c.feedback).length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                    
                    {/* Strengths */}
                    {c.feedback.strengths?.length > 0 && (
                      <div className="feedback-section">
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#15803d', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          ✔ Strengths
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {c.feedback.strengths.map((s, i) => (
                            <div key={i} style={{ fontSize: 13.5, color: 'var(--text-primary)', display: 'flex', gap: 8 }}>
                              <span style={{ color: '#22c55e' }}>•</span>
                              <span>{s}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Weaknesses / Gaps */}
                    {c.feedback.weaknesses?.length > 0 && (
                      <div className="feedback-section">
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#dc2626', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          ⚠ Weaknesses / Gaps
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {c.feedback.weaknesses.map((w, i) => (
                            <div key={i} style={{ fontSize: 13.5, color: 'var(--text-primary)', display: 'flex', gap: 8 }}>
                              <span style={{ color: '#ef4444' }}>•</span>
                              <span>{w}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Technical Assessment */}
                    {c.feedback.assessment?.length > 0 && (
                      <div className="feedback-section">
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#6366f1', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          🔬 Technical Assessment
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {c.feedback.assessment.map((a, i) => (
                            <div key={i} style={{ fontSize: 13.5, color: 'var(--text-primary)', display: 'flex', gap: 8 }}>
                              <span style={{ color: '#818cf8' }}>•</span>
                              <span>{a}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Suitability */}
                    <div style={{ padding: 14, background: '#f0f9ff', borderRadius: 10, border: '1px solid #bae6fd' }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: '#0369a1', marginBottom: 4, textTransform: 'uppercase' }}>
                        Role Suitability
                      </div>
                      <div style={{ fontSize: 13.5, color: '#0c4a6e', fontWeight: 600 }}>
                        {c.feedback.suitability}
                      </div>
                    </div>

                    {/* Verdict */}
                    <div style={{ marginTop: 4 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 6 }}>Overall Verdict</div>
                      <div style={{ 
                        fontSize: 14, fontStyle: 'italic', color: 'var(--text-primary)', 
                        padding: '12px 16px', background: '#fff', borderLeft: '4px solid #6366f1', 
                        borderRadius: '0 8px 8px 0', boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
                      }}>
                        "{c.feedback.verdict}"
                      </div>
                    </div>

                  </div>
                ) : c.feedback && typeof c.feedback === 'string' ? (
                   /* Handle legacy string feedback if it exists */
                   <div style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text-primary)' }}>
                    {c.feedback.split('\n').map((line, i) => {
                      const isHeader = line.endsWith(':') && !line.startsWith('-');
                      return (
                        <p key={i} style={{ 
                          marginBottom: isHeader ? 8 : 4,
                          fontWeight: isHeader ? 700 : 400,
                          color: isHeader ? 'var(--text-primary)' : 'var(--text-secondary)',
                          fontSize: isHeader ? 14 : 13.5
                        }}>
                          {line}
                        </p>
                      );
                    })}
                  </div>
                ) : (
                  <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                    Feedback not generated yet. Run ranking first to generate AI insights.
                  </p>
                )}
              </div>

              {/* Education & Experience */}
              <div className="card">
                <h3 style={{ marginBottom: 14, fontSize: 15, fontWeight: 700 }}>📚 Background</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Education</div>
                    {c.education?.length > 0
                      ? c.education.map(e => <SkillChip key={e} skill={e} variant="neutral" />)
                      : <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Not detected</span>}
                  </div>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Experience</div>
                    {/* Red if 0 years, colored by score otherwise */}
                    <span style={{ fontSize: 22, fontWeight: 800, color: expColor }}>
                      {expYears}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}> years</span>
                    {expYears <= 0 && (
                      <div style={{ fontSize: 11, color: '#ef4444', marginTop: 2 }}>No experience detected</div>
                    )}
                  </div>
                </div>
              </div>

              {/* Interview Preparation */}
              <InterviewPrepCard candidateId={id} jobId={c.job_id} jobTitle={c.job_title} />

              {/* HR Notes */}
              <div className="card">
                <h3 style={{ marginBottom: 12, fontSize: 15, fontWeight: 700 }}>📝 HR Notes</h3>
                {c.notes?.length > 0 && (
                  <div style={{ marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {c.notes.map((n, i) => (
                      <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8, fontSize: 13 }}>
                        <div style={{ color: 'var(--text-secondary)', fontSize: 11, marginBottom: 2 }}>
                          {n.author} · {n.created_at?.slice(0, 10)}
                        </div>
                        <div>{n.text}</div>
                      </div>
                    ))}
                  </div>
                )}
                <form onSubmit={addNote} style={{ display: 'flex', gap: 8 }}>
                  <input className="form-input" style={{ flex: 1 }}
                    placeholder="Add a note…" value={note}
                    onChange={e => setNote(e.target.value)} />
                  <button type="submit" className="btn btn-primary btn-sm" disabled={savingNote}>
                    <MdSend />
                  </button>
                </form>
              </div>
            </div>

            {/* ── RIGHT COLUMN ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

              {/* Actions */}
              <div className="card">
                <h3 style={{ marginBottom: 14, fontSize: 15, fontWeight: 700 }}>Actions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <button className="btn btn-outline" style={{ justifyContent: 'center' }}
                    onClick={() => updateStatus('pending')}>
                    Pending
                  </button>
                  <button className="btn btn-success" style={{ justifyContent: 'center' }}
                    onClick={() => updateStatus('shortlisted')}>
                    <MdThumbUp /> Shortlist Candidate
                  </button>
                  <button className="btn btn-info" style={{ justifyContent: 'center' }}
                    onClick={() => setShowInterview(true)}>
                    <MdCalendarToday /> Schedule Interview
                  </button>
                  <button className="btn btn-purple" style={{ justifyContent: 'center' }}
                    onClick={() => updateStatus('selected')}>
                    <MdCheckCircle /> Mark as Selected
                  </button>
                  <button className="btn btn-danger" style={{ justifyContent: 'center' }}
                    onClick={() => updateStatus('rejected')}>
                    <MdThumbDown /> Reject Candidate
                  </button>
                </div>

                <button className="btn btn-outline" style={{ justifyContent: 'center', borderColor: 'var(--danger)', color: 'var(--danger)', marginTop: 8 }}
                    onClick={() => {
                      if (window.confirm('Are you sure you want to delete this candidate?')) {
                        API.delete(`/candidates/${id}`).then(() => {
                          toast.success('Candidate deleted');
                          navigate(-1);
                        }).catch((err) => {
                          console.error(err);
                          toast.error('Failed to delete candidate');
                        });
                      }
                    }}>
                    <MdDelete /> Delete Candidate
                  </button>
                </div>
                
                {/* Activity History */}
                <div className="card">
                  <h3 style={{ marginBottom: 12, fontSize: 15, fontWeight: 700 }}>🕒 Activity History</h3>
                  {c.activity_history?.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, position: 'relative' }}>
                      {/* Vertical line connecting timeline dots */}
                      <div style={{ position: 'absolute', top: 8, bottom: 8, left: 5, width: 2, background: '#e2e8f0', zIndex: 0 }} />
                      
                      {/* Sort history descending (newest first) */}
                      {[...c.activity_history].reverse().map((act, i) => (
                        <div key={i} style={{ display: 'flex', gap: 12, position: 'relative', zIndex: 1 }}>
                          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#6366f1', border: '2px solid #fff', marginTop: 4, flexShrink: 0 }} />
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{act.action}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                              {act.author || 'System'} · {new Date(act.timestamp).toLocaleString(undefined, {
                                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                              })}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>No recent activity.</p>
                  )}
                </div>

                <ResumePreview id={id} filename={c.filename} />

                {/* Interview Details */}
                {c.interview && (
                  <div className="card">
                    <h3 style={{ marginBottom: 14, fontSize: 15, fontWeight: 700 }}>📅 Interview Details</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
                      <div><span style={{ color: 'var(--text-secondary)' }}>Date: </span><b>{c.interview.date}</b></div>
                      <div><span style={{ color: 'var(--text-secondary)' }}>Time: </span><b>{c.interview.time}</b></div>
                      <div><span style={{ color: 'var(--text-secondary)' }}>Mode: </span>
                        <SkillChip skill={c.interview.mode} variant="neutral" />
                      </div>
                      {c.interview.location && (
                        <div><span style={{ color: 'var(--text-secondary)' }}>Location: </span>{c.interview.location}</div>
                      )}
                      {c.interview.meeting_link && (
                        <div style={{ marginTop: 8, padding: 12, background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0' }}>
                          <div style={{ marginBottom: 8, fontWeight: 600, color: '#166534', fontSize: 13 }}>🎥 Video Call</div>
                          <div style={{ display: 'flex', gap: 8 }}>
                            <button className="btn btn-success btn-sm" style={{ flex: 1 }} onClick={startInterview}>
                              {isInterviewing ? '🟢 Monitoring...' : 'Start Interview'}
                            </button>
                            <button className="btn btn-outline btn-sm" onClick={() => {
                              navigator.clipboard.writeText(c.interview.meeting_link);
                              toast.success('Link copied');
                            }}>Copy</button>
                          </div>
                        </div>
                      )}

                      {/* Live monitoring panel */}
                      {isInterviewing && (
                        <div style={{ marginTop: 12 }}>
                          <InterviewMonitor candidateId={id} />
                          <button className="btn btn-danger btn-sm" style={{ width: '100%', marginTop: 8 }}
                            onClick={endInterview}>
                            ⏹ End Interview & Analyze
                          </button>
                        </div>
                      )}

                      {c.interview.notes && (
                        <div style={{ marginTop: 4 }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Notes: </span>{c.interview.notes}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* AI Interview Analysis */}
                <InterviewInsightCard candidate={c} />

              </div> {/* Close Right Column */}
            </div> {/* Close Grid */}
          </div> {/* Close Page Body */}
        </div> {/* Close Main Content */}

        {showInterview && (
          <InterviewModal
            candidate={c}
            onClose={() => setShowInterview(false)}
            onSuccess={fetchCandidate}
          />
        )}
      </div> // Close Layout
  );
}
