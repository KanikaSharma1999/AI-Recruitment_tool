import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import StatusBadge from '../components/StatusBadge';
import InterviewModal from '../components/InterviewModal';
import InterviewMonitor from '../components/InterviewMonitor';
import ScoreDimensions from '../components/ScoreDimensions';
import HiringSummaryCard from '../components/HiringSummaryCard';
import InterviewInsightCard from '../components/InterviewInsightCard';
import API from '../api/client';
import toast from 'react-hot-toast';
import { 
  MdArrowBack, MdCalendarToday, MdThumbUp, MdThumbDown, MdCheckCircle,
  MdSend, MdDelete, MdOpenInNew, MdInfoOutline, MdExpandMore, MdExpandLess,
  MdContentCopy, MdEmail, MdShare, MdPerson, MdLocationOn, MdPhone,
  MdLayers, MdChatBubble, MdAccessTime, MdArticle, MdListAlt
} from 'react-icons/md';

// ── Score helpers ─────────────────────────────────────────────────────────────
const safeScore = (value) => {
  if (value === null || value === undefined || value === '') return 0;
  return Math.min(100, Math.max(0, Math.round(Number(value))));
};

const getColor = (score) => {
  if (score > 80) return '#10b981';
  if (score > 50) return '#f59e0b';
  return '#ef4444';
};

// ── Resume Preview Component ──────────────────────────────────────────────────
const ResumePreview = ({ id, filename }) => {
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const url = `${API.defaults.baseURL}/candidates/${id}/resume`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: '#334155' }}>File: {filename}</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button 
            className="btn btn-sm btn-outline"
            onClick={() => window.open(url, '_blank')}
            style={{ fontSize: 12 }}
          >
            <MdOpenInNew /> Open External
          </button>
          <a 
            href={url} 
            download 
            className="btn btn-sm btn-outline"
            style={{ textDecoration: 'none', color: 'inherit', fontSize: 12 }}
          >
            Download Original PDF
          </a>
        </div>
      </div>

      <div style={{ 
        height: 600, background: '#f8fafc', borderRadius: 12, 
        border: '1px solid #e2e8f0', overflow: 'hidden', position: 'relative',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        {loading && !error && (
          <div style={{ position: 'absolute', textAlign: 'center', zIndex: 10 }}>
            <div className="spinner" style={{ margin: '0 auto 10px' }} />
            <div style={{ fontSize: 12, color: '#64748b' }}>Loading resume preview...</div>
          </div>
        )}

        {error ? (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <MdInfoOutline size={40} style={{ color: '#94a3b8', marginBottom: 10 }} />
            <div style={{ fontWeight: 700, marginBottom: 4 }}>Resume File Not Found</div>
            <div style={{ fontSize: 13, color: '#64748b', maxWidth: 250 }}>
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

// ── Clean score bar ───────────────────────────────────────────────────────────
const ScoreBar = ({ label, score, tooltip }) => {
  const s = safeScore(score);
  const [showTip, setShowTip] = useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#475569', display: 'flex', alignItems: 'center', gap: 4 }}>
          {label}
          {tooltip && (
            <span
              style={{ position: 'relative', cursor: 'help' }}
              onMouseEnter={() => setShowTip(true)}
              onMouseLeave={() => setShowTip(false)}
            >
              <MdInfoOutline style={{ fontSize: 13, color: '#94a3b8', verticalAlign: 'middle' }} />
              {showTip && (
                <span style={{
                  position: 'absolute', left: 20, top: -4, zIndex: 10,
                  background: '#1e293b', color: '#fff', fontSize: 10,
                  padding: '4px 8px', borderRadius: 6, whiteSpace: 'nowrap', boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                }}>{tooltip}</span>
              )}
            </span>
          )}
        </span>
        <span style={{ fontWeight: 800, color: getColor(s), fontSize: 14 }}>{s}%</span>
      </div>
      <div style={{ height: 6, background: '#f1f5f9', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${s}%`, backgroundColor: getColor(s),
          borderRadius: 999, transition: 'width 0.6s cubic-bezier(0.4,0,0.2,1)' }} />
      </div>
    </div>
  );
};

// ── Skill chip variants ───────────────────────────────────────────────────────
const SkillChip = ({ skill, variant }) => {
  const styles = {
    required: { background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' },
    matched:  { background: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0' },
    missing:  { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' },
    neutral:  { background: '#f8fafc', color: '#334155', border: '1px solid #e2e8f0' },
  };
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: 20,
      fontSize: 11.5,
      fontWeight: 600,
      margin: '2px 4px 2px 0',
      ...styles[variant || 'neutral'],
    }}>
      {skill}
    </span>
  );
};

const TranscriptModal = ({ candidate, onClose }) => {
  const transcript = candidate.transcript || [];
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(8px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: 20
    }} onClick={onClose}>
      <div style={{
        background: '#ffffff', borderRadius: 16, width: '100%', maxWidth: 700,
        height: '80vh', display: 'flex', flexDirection: 'column', overflow: 'hidden',
        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)', border: '1px solid #e2e8f0'
      }} onClick={e => e.stopPropagation()}>
        <div style={{ padding: '16px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700 }}>Interview Transcript Stream — {candidate.name}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose} style={{ minWidth: 'auto', padding: 6 }}><MdClose size={20} /></button>
        </div>
        <div style={{ flex: 1, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {transcript.length > 0 ? transcript.map((line, idx) => {
            const isObj = typeof line === 'object' && line !== null;
            const text = isObj ? line.text : line;
            const speaker = isObj ? (line.speaker || 'Candidate') : 'Candidate';
            const timestamp = isObj ? (line.timestamp || '') : '';
            const isInterviewer = speaker === 'Interviewer';

            return (
              <div key={idx} style={{ 
                display: 'flex', gap: 10, alignItems: 'flex-start', maxWidth: '85%',
                alignSelf: isInterviewer ? 'flex-end' : 'flex-start',
                flexDirection: isInterviewer ? 'row-reverse' : 'row'
              }}>
                <div style={{ 
                  width: '28px', height: '28px', borderRadius: '50%', 
                  background: isInterviewer ? '#d1fae5' : '#e0e7ff', 
                  color: isInterviewer ? '#065f46' : '#4f46e5', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700
                }}>
                  {speaker[0]}
                </div>
                <div style={{ 
                  background: isInterviewer ? '#ecfdf5' : '#f3f4f6', 
                  padding: '10px 14px', borderRadius: 12, border: `1px solid ${isInterviewer ? '#a7f3d0' : '#e5e7eb'}` 
                }}>
                  <div style={{ display: 'flex', gap: 12, marginBottom: 4, fontSize: 10, color: '#6b7280', fontWeight: 500 }}>
                    <span style={{ fontWeight: 600, color: isInterviewer ? '#065f46' : '#4f46e5' }}>{speaker} {timestamp && `[${timestamp}]`}</span>
                  </div>
                  <div style={{ fontSize: 13, color: '#1f2937', lineHeight: 1.5 }}>{text}</div>
                </div>
              </div>
            );
          }) : (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#94a3b8' }}>No transcript available for this candidate.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default function CandidateProfile() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [c, setC] = useState(null);
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [note, setNote] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [showInterview, setShowInterview] = useState(false);
  const [showTranscriptModal, setShowTranscriptModal] = useState(false);
  const [showRecording, setShowRecording] = useState(false);

  // Tab Control
  const [activeTab, setActiveTab] = useState('overview');

  const fetchCandidate = async () => {
    try {
      const r = await API.get(`/candidates/${id}`);
      setC(r.data);
      if (r.data?.job_id) {
        const jr = await API.get(`/jobs/${r.data.job_id}`);
        setJob(jr.data);
      }
    } catch (err) {
      toast.error('Candidate not found');
      navigate('/candidates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidate();
  }, [id]);

  const updateStatus = async (status) => {
    try {
      await API.put(`/candidates/${id}/status`, { status });
      toast.success(`Pipeline status updated to ${status}`);
      fetchCandidate();
    } catch {
      toast.error('Failed to update stage');
    }
  };

  const addNote = async (e) => {
    e.preventDefault();
    if (!note.trim()) return;
    setSavingNote(true);
    try {
      await API.post(`/candidates/${id}/notes`, { text: note });
      toast.success('Note recorded');
      setNote('');
      fetchCandidate();
    } catch {
      toast.error('Failed to record comment');
    } finally {
      setSavingNote(false);
    }
  };

  const startInterview = () => {
    navigate(`/interview-room/${id}`);
  };

  const downloadReport = async () => {
    try {
      const r = await API.get(`/report/candidate/${id}`, { responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${c.name}_interview_report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download report');
    }
  };

  if (loading) {
    return (
      <div className="layout">
        <Sidebar />
        <div className="main-content flex-center">
          <div className="spinner" />
        </div>
      </div>
    );
  }

  if (!c) return null;

  const isInterviewing = c.status === 'interview_scheduled' || c.status === 'interview_live';
  
  // Expiry check
  let isMissed = false;
  if (c.interview && c.interview.date && c.interview.time && c.status === 'interview_scheduled') {
    try {
      const interviewISO = `${c.interview.date}T${c.interview.time}:00`;
      const interviewTime = new Date(interviewISO).getTime();
      const expirationLimit = interviewTime + 15 * 60 * 1000;
      if (Date.now() > expirationLimit) {
        isMissed = true;
      }
    } catch {}
  }

  const overall = safeScore(c.ai_match_score !== undefined && c.ai_match_score !== null ? c.ai_match_score : c.score);
  const ringColor = getColor(overall);

  // Extract explanation details
  const expl = c.match_explanation || {};
  const exactMatches = c.exact_matches || expl.exact_matches || [];
  const semanticMatches = c.semantic_matches || expl.semantic_matches || [];
  const partialMatches = c.partial_matches || expl.partial_matches || [];
  const missingSkills = c.missing_skills || expl.missing_skills || [];
  const bonusSkills = c.bonus_skills || expl.bonus_skills || [];
  const projectsList = c.projects || expl.projects || [];
  const certsList = c.certifications || expl.certifications || [];
  const expYears = c.experience_years !== undefined ? c.experience_years : (c.experience || 0);

  return (
    <div className="layout font-inter">
      <Sidebar />
      <div className="main-content" style={{ display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
        
        {/* Sticky Profile Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 32px',
          borderBottom: '1px solid #e2e8f0',
          background: '#ffffff',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <button 
              onClick={() => navigate(-1)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', display: 'flex', alignItems: 'center', padding: 6 }}
            >
              <MdArrowBack size={20} />
            </button>
            <div style={{
              width: 42,
              height: 42,
              borderRadius: '50%',
              background: `conic-gradient(${ringColor} ${overall * 3.6}deg, #e2e8f0 0deg)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 0 3px ${ringColor}18`
            }}>
              <div style={{
                width: 34, height: 34, borderRadius: '50%', background: '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, color: '#0f172a'
              }}>
                {overall}%
              </div>
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <h1 className="tracking-tight" style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>{c.name}</h1>
                <span className={`badge badge-${c.status?.toLowerCase().replace(' ', '-')}`} style={{ fontWeight: 700 }}>
                  {c.status?.toUpperCase()?.replace('_', ' ')}
                </span>
              </div>
              <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                Applied for <b>{job?.title || c.job_title || 'General Position'}</b> · {c.location || 'Remote'}
              </div>
            </div>
          </div>

          {/* Quick stage transition drop-down + actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '0 8px', height: 32 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b' }}>STAGE:</span>
              <select
                value={c.status || 'applied'}
                onChange={e => updateStatus(e.target.value)}
                style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 12, fontWeight: 600, color: '#334155', cursor: 'pointer' }}
              >
                <option value="applied">Applied</option>
                <option value="screening">Screening</option>
                <option value="shortlisted">Shortlisted</option>
                <option value="interview_scheduled">Interview</option>
                <option value="interview_completed">Completed</option>
                <option value="offered">Offered</option>
                <option value="hired">Hired</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <button className="btn btn-outline btn-sm" onClick={() => setShowInterview(true)}>
              <MdCalendarToday /> Schedule
            </button>

            {c.interview && (c.interview.status === 'completed' || c.status === 'interview_completed' || c.status === 'interview_analyzed') && (
              <button className="btn btn-outline btn-sm" onClick={downloadReport}>
                Download PDF
              </button>
            )}

            <button 
              className="btn btn-danger btn-sm"
              onClick={() => {
                if (window.confirm('Delete this candidate permanently?')) {
                  API.delete(`/candidates/${id}`).then(() => {
                    toast.success('Candidate deleted');
                    navigate('/candidates');
                  }).catch(() => toast.error('Failed to delete candidate'));
                }
              }}
            >
              Delete
            </button>

          </div>
        </div>

        {/* Tabbed Candidate Layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '3fr 1.1fr', gap: 24, padding: 32, flex: 1, overflowY: 'auto' }}>
          
          {/* LEFT AREA: Tabs & Dynamic Panel */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            
            {/* Lever-style tabs */}
            <div className="ent-tabs">
              {[
                { id: 'overview', label: 'Overview', icon: <MdPerson /> },
                { id: 'resume', label: 'Resume File', icon: <MdArticle /> },
                { id: 'match', label: 'AI Match Analysis', icon: <MdLayers /> },
                { id: 'skills', label: 'Skills Alignment', icon: <MdListAlt /> },
                { id: 'interview', label: 'Interview Reports', icon: <MdCalendarToday /> },
              ].map(t => (
                <button
                  key={t.id}
                  className={`ent-tab ${activeTab === t.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(t.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  {t.icon}
                  {t.label}
                </button>
              ))}
            </div>

            {/* TAB PANELS */}
            
            {/* Tab 1: Overview */}
            {activeTab === 'overview' && (
              <div className="animate-fade" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                
                {/* Profile Meta Cards */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                  <div className="ent-card" style={{ padding: 16 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Contact Email</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a', marginTop: 4 }}>{c.email}</div>
                  </div>
                  <div className="ent-card" style={{ padding: 16 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Phone Number</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a', marginTop: 4 }}>{c.phone || 'N/A'}</div>
                  </div>
                  <div className="ent-card" style={{ padding: 16 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Experience Experience</div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#0f172a', marginTop: 4 }}>{expYears} Years</div>
                  </div>
                </div>

                {/* Recruiter Activity Timeline */}
                <div className="ent-card">
                  <div className="ent-card-header">
                    <span className="ent-card-title">Candidate Activity Log</span>
                  </div>
                  {c.activity_history && c.activity_history.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14, position: 'relative', paddingLeft: 12 }}>
                      <div style={{ position: 'absolute', top: 6, bottom: 6, left: 16, width: 1.5, background: '#e2e8f0' }} />
                      {[...c.activity_history].reverse().map((act, i) => (
                        <div key={i} style={{ display: 'flex', gap: 16, position: 'relative' }}>
                          <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#4f46e5', border: '2px solid #fff', marginTop: 4, zIndex: 1, boxShadow: '0 0 0 3px rgba(79,70,229,0.1)' }} />
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>{act.action}</div>
                            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                              Performed by <b>{act.author || 'System'}</b> · {new Date(act.timestamp).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: 24, color: '#94a3b8', fontSize: 12 }}>No activity recorded yet.</div>
                  )}
                </div>

              </div>
            )}

            {/* Tab 2: Resume Preview */}
            {activeTab === 'resume' && (
              <div className="ent-card animate-fade">
                <ResumePreview id={id} filename={c.filename} />
              </div>
            )}

            {/* Tab 3: AI Match Analysis */}
            {activeTab === 'match' && (
              <div className="animate-fade" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                
                <div className="ent-card" style={{ display: 'flex', gap: 32, alignItems: 'center' }}>
                  <div style={{
                    width: 110, height: 110, borderRadius: '50%',
                    background: `conic-gradient(${ringColor} ${overall * 3.6}deg, #f1f5f9 0deg)`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    boxShadow: `0 0 0 8px ${ringColor}12`,
                  }}>
                    <div style={{ width: 86, height: 86, borderRadius: '50%', background: '#fff', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ fontSize: 26, fontWeight: 900, color: ringColor }}>{overall}%</span>
                      <span style={{ fontSize: 9, color: '#64748b', fontWeight: 700 }}>AI MATCH</span>
                    </div>
                  </div>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a' }}>AI Match Recommendation</h3>
                    <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, marginTop: 4 }}>
                      {c.recruiter_explanation || (overall >= 75 ? 'Strong recommendation for hire based on skill matches and domain semantic relevance.' : overall >= 50 ? 'Recommended for next-stage screening. Candidate matches key core competencies but lacks a few optional skill components.' : 'Candidate fails to meet core requirements. Penalty points applied due to significant skill gap.')}
                    </p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                  <div className="ent-card">
                    <div className="ent-card-title" style={{ marginBottom: 16 }}>Score Breakdown</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                      <ScoreBar label="Skills Fit" score={c.skills_score !== undefined ? c.skills_score : c.skill_score} tooltip="Core required skill coverage" />
                      <ScoreBar label="Experience Depth" score={c.experience_score} tooltip="Candidate experience vs. required years" />
                      <ScoreBar label="Semantic Similarity" score={c.semantic_score} tooltip="Contextual overlap between resume and description" />
                      <ScoreBar label="Projects Score" score={c.projects_score !== undefined ? c.projects_score : c.project_score} tooltip="Assessed projects matching JD" />
                      <ScoreBar label="Certifications Score" score={c.certification_score !== undefined ? c.certification_score : c.cert_score} tooltip="Extra credits for required certifications" />
                    </div>
                  </div>

                  <div className="ent-card">
                    <div className="ent-card-title" style={{ marginBottom: 16 }}>Extracted Credentials</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                      <div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginBottom: 4 }}>Extracted Projects</div>
                        {projectsList.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {projectsList.map((p, i) => <div key={i} style={{ fontSize: 12, color: '#334155' }}>• {p}</div>)}
                          </div>
                        ) : <span style={{ fontSize: 12, color: '#94a3b8' }}>None detected</span>}
                      </div>

                      <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginBottom: 4 }}>Extracted Certifications</div>
                        {certsList.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {certsList.map((cr, i) => <div key={i} style={{ fontSize: 12, color: '#334155' }}>• {cr}</div>)}
                          </div>
                        ) : <span style={{ fontSize: 12, color: '#94a3b8' }}>None detected</span>}
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            )}

            {/* Tab 4: Skills Alignment */}
            {activeTab === 'skills' && (
              <div className="ent-card animate-fade">
                <div className="ent-card-title" style={{ marginBottom: 16 }}>Skills Breakdown</div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#16a34a', marginBottom: 8 }}>✅ MATCHED SKILLS ({exactMatches.length + semanticMatches.length + partialMatches.length})</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {exactMatches.map(s => <SkillChip key={s} skill={s} variant="matched" />)}
                      {semanticMatches.map(s => <SkillChip key={s} skill={s} variant="matched" />)}
                      {partialMatches.map(s => <SkillChip key={s} skill={s} variant="matched" />)}
                    </div>
                  </div>

                  {missingSkills.length > 0 && (
                    <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#dc2626', marginBottom: 8 }}>❌ MISSING SKILLS ({missingSkills.length})</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {missingSkills.map(s => <SkillChip key={s} skill={s} variant="missing" />)}
                      </div>
                    </div>
                  )}

                  {bonusSkills.length > 0 && (
                    <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#0891b2', marginBottom: 8 }}>💎 BONUS SKILLS ({bonusSkills.length})</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {bonusSkills.map(s => <SkillChip key={s} skill={s} variant="neutral" />)}
                      </div>
                    </div>
                  )}

                  <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#475569', marginBottom: 8 }}>ALL EXTRACTED SKILLS ({c.skills?.length || 0})</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {(c.skills || []).map(s => <SkillChip key={s} skill={s} variant="neutral" />)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 5: Interview Reports */}
            {activeTab === 'interview' && (
              <div className="animate-fade" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                
                {/* Scheduling Details */}
                {c.interview ? (
                  <div className="ent-card">
                    <div className="ent-card-header">
                      <span className="ent-card-title">Interview Session Details</span>
                      <span className={`badge badge-${c.interview.status || 'scheduled'}`}>
                        {(c.interview.status || 'scheduled').toUpperCase()}
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: 13, color: '#334155' }}>
                      <div>
                        <div style={{ color: '#64748b', fontSize: 11, fontWeight: 700 }}>DATE & TIME</div>
                        <div style={{ marginTop: 4, fontWeight: 600 }}>{c.interview.date} at {c.interview.time}</div>
                      </div>
                      <div>
                        <div style={{ color: '#64748b', fontSize: 11, fontWeight: 700 }}>INTERVIEW MODE</div>
                        <div style={{ marginTop: 4, fontWeight: 600 }}>{c.interview.mode?.toUpperCase()}</div>
                      </div>
                    </div>

                    {c.interview.meeting_link && (
                      <div style={{ marginTop: 16, borderTop: '1px solid #f1f5f9', paddingTop: 16 }}>
                        {c.interview.status === 'completed' || c.status === 'interview_completed' || c.status === 'interview_analyzed' ? (
                          <div style={{ display: 'flex', gap: 8 }}>
                            <button className="btn btn-primary btn-sm" onClick={() => setShowTranscriptModal(true)}>
                              View Full Transcript
                            </button>
                            <button className="btn btn-outline btn-sm" onClick={() => setShowRecording(!showRecording)}>
                              {showRecording ? 'Hide Waveform' : 'Play Audio Recording'}
                            </button>
                          </div>
                        ) : (
                          <div>
                            {isMissed ? (
                              <div style={{ padding: 12, background: '#fef2f2', borderRadius: 8, border: '1px solid #fecaca', color: '#b91c1c' }}>
                                <b>Missed Session:</b> The scheduled slot has expired. Please reschedule.
                              </div>
                            ) : (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                <button className="btn btn-success btn-sm" onClick={startInterview}>
                                  Launch Video Monitor Room
                                </button>
                                <div style={{ display: 'flex', gap: 8 }}>
                                  <input 
                                    className="form-input" 
                                    readOnly 
                                    value={c.interview.meeting_link} 
                                    style={{ flex: 1, fontSize: 12, height: 32 }} 
                                  />
                                  <button 
                                    className="btn btn-outline btn-sm" 
                                    onClick={() => {
                                      navigator.clipboard.writeText(c.interview.meeting_link);
                                      toast.success('Interview link copied');
                                    }}
                                  >
                                    Copy Link
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="ent-card" style={{ padding: 24, textAlign: 'center', color: '#64748b' }}>
                    <div style={{ fontSize: 13, marginBottom: 12 }}>No interview has been scheduled for this candidate.</div>
                    <button className="btn btn-primary btn-sm" onClick={() => setShowInterview(true)}>
                      Schedule Video Interview
                    </button>
                  </div>
                )}

                {/* Simulated Wave Player */}
                {showRecording && (
                  <div className="ent-card animate-fade" style={{ background: '#0f172a', border: '1px solid #1e293b', color: '#ffffff' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8' }}>AUDIO PLAYBACK</span>
                      <span style={{ fontSize: 9, background: '#22c55e', color: '#fff', padding: '1px 4px', borderRadius: 4 }}>READY</span>
                    </div>
                    <div style={{ height: 50, background: 'rgba(30,41,59,0.5)', display: 'flex', alignItems: 'center', gap: 2, padding: 8, borderRadius: 6 }}>
                      {[25,45,15,65,75,40,90,20,50,60,30,80,40,20,10,35,55,75,45,95,30,60,40,75,20,10].map((h, i) => (
                        <div key={i} style={{ width: 3, height: `${h}%`, background: '#6366f1', borderRadius: 2 }} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Behavioral AI Feedback Card */}
                {c.ai_analysis && (
                  <div className="ent-card">
                    <div className="ent-card-title" style={{ marginBottom: 16 }}>AI Behavioral Assessment</div>
                    <InterviewInsightCard candidate={c} />
                  </div>
                )}

              </div>
            )}

          </div>

          {/* RIGHT COLUMN: Candidate Contact & Recruiter Comments */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            
            {/* Quick Profile Summary Card */}
            <div className="ent-card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Profile Info</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13, color: '#475569' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <MdLocationOn style={{ color: '#94a3b8' }} /> {c.location || 'Remote'}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <MdEmail style={{ color: '#94a3b8' }} /> {c.email}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <MdPhone style={{ color: '#94a3b8' }} /> {c.phone || 'No phone'}
                </div>
              </div>

              {c.education && c.education.length > 0 && (
                <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: 12 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6 }}>Education</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {c.education.map((e, idx) => <span key={idx} style={{ fontSize: 11, background: '#f1f5f9', padding: '2px 8px', borderRadius: 4, color: '#475569' }}>{e}</span>)}
                  </div>
                </div>
              )}
            </div>

            {/* Recruiter Notes Block */}
            <div className="ent-card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="ent-card-header" style={{ marginBottom: 12 }}>
                <span className="ent-card-title">Recruiter Comments</span>
                <MdChatBubble size={16} style={{ color: '#94a3b8' }} />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 300, overflowY: 'auto', marginBottom: 12 }}>
                {c.notes && c.notes.length > 0 ? c.notes.map((n, i) => (
                  <div key={i} style={{ padding: '8px 10px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 12.5 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#94a3b8', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, color: '#64748b' }}>{n.author}</span>
                      <span>{n.created_at?.slice(0, 10)}</span>
                    </div>
                    <div style={{ color: '#1e293b' }}>{n.text}</div>
                  </div>
                )) : (
                  <div style={{ padding: '16px 0', textAlign: 'center', color: '#94a3b8', fontSize: 12 }}>No notes added.</div>
                )}
              </div>

              <form onSubmit={addNote} style={{ display: 'flex', gap: 6 }}>
                <input 
                  className="form-input" 
                  style={{ flex: 1, height: 32, fontSize: 12, borderRadius: 6 }}
                  placeholder="Type note..." 
                  value={note}
                  onChange={e => setNote(e.target.value)} 
                />
                <button type="submit" className="btn btn-primary btn-sm" style={{ height: 32, padding: '0 10px' }} disabled={savingNote}>
                  <MdSend size={14} />
                </button>
              </form>
            </div>

          </div>

        </div>

      </div>

      {showInterview && (
        <InterviewModal
          candidate={c}
          onClose={() => setShowInterview(false)}
          onSuccess={fetchCandidate}
        />
      )}

      {showTranscriptModal && (
        <TranscriptModal
          candidate={c}
          onClose={() => setShowTranscriptModal(false)}
        />
      )}

    </div>
  );
}
