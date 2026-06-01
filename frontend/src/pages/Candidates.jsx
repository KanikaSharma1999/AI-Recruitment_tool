import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import StatusBadge from '../components/StatusBadge';
import InterviewModal from '../components/InterviewModal';
import API from '../api/client';
import toast from 'react-hot-toast';
import { MdSearch, MdVisibility, MdThumbUp, MdThumbDown, MdCalendarToday, MdCheckCircle, MdFilterList, MdDownload, MdDelete, MdViewList, MdViewKanban } from 'react-icons/md';
import KanbanBoard from '../components/KanbanBoard';

const STATUSES = [
  { value: 'All', label: 'All' },
  { value: 'applied', label: 'Applied' },
  { value: 'screening', label: 'Screening' },
  { value: 'shortlisted', label: 'Shortlisted' },
  { value: 'interview_scheduled', label: 'Interview Scheduled' },
  { value: 'interview_completed', label: 'Interview Completed' },
  { value: 'offered', label: 'Offered' },
  { value: 'hired', label: 'Hired' },
  { value: 'rejected', label: 'Rejected' }
];

export default function Candidates() {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('pipeline');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [jobFilter, setJobFilter] = useState('');
  const [minScore, setMinScore] = useState('');
  const [maxScore, setMaxScore] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [skillFilter, setSkillFilter] = useState('');
  const [interviewCandidate, setInterviewCandidate] = useState(null);
  const navigate = useNavigate();

  const fetchCandidates = async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (jobFilter) params.set('job_id', jobFilter);
    if (statusFilter !== 'All') params.set('status', statusFilter);
    if (minScore) params.set('min_score', parseFloat(minScore));
    if (maxScore) params.set('max_score', parseFloat(maxScore));
    if (locationFilter) params.set('location', locationFilter);
    if (skillFilter) params.set('skill', skillFilter);
    if (search) params.set('search', search);
    try {
      const r = await API.get(`/candidates/list?${params}`);
      setCandidates(r.data);
    } catch { toast.error('Failed to load candidates'); }
    finally { setLoading(false); }
  };

  useEffect(() => { API.get('/jobs/list').then(r => setJobs(r.data)).catch(() => {}); }, []);
  useEffect(() => { fetchCandidates(); }, [statusFilter, jobFilter]);

  const handleSearch = (e) => { e.preventDefault(); fetchCandidates(); };

  const updateStatus = async (id, status) => {
    try {
      await API.put(`/candidates/${id}/status`, { status });
      toast.success(`Moved to ${status}`);
      fetchCandidates();
    } catch { toast.error('Failed to update status'); }
  };

  const handleRerankAll = async () => {
    const loadingToast = toast.loading('Re-ranking candidates and processing embeddings...');
    try {
      await API.post('/rerank-all-candidates');
      toast.success('Successfully re-ranked all candidates!', { id: loadingToast });
      fetchCandidates();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to re-rank candidates', { id: loadingToast });
    }
  };

  const downloadReport = async (fmt) => {
    const params = jobFilter ? `?format=${fmt}&job_id=${jobFilter}` : `?format=${fmt}`;
    const r = await API.get(`/report/download${params}`, { responseType: 'blob' });
    const url = URL.createObjectURL(r.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `candidates_report.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Scores are stored as 0-100 in MongoDB
  const getColor = (s) => {
    if (s > 85) return '#22c55e';   // green
    if (s > 45) return '#f59e0b';   // yellow
    return '#ef4444';               // red
  };

  // Scores are stored as 0-100 in MongoDB — just clamp and round
  const safeScore = (v) => {
    if (!v && v !== 0) return 0;
    return Math.min(100, Math.max(0, Math.round(Number(v))));
  };

  const getCandidateJDStatus = (c) => {
    const candJob = jobs.find(j => j.id === c.job_id || j._id === c.job_id);
    const jdExists = !!(candJob && candJob.description && candJob.description.trim());
    return { jdExists, candJob };
  };

  const renderCandidateScore = (c) => {
    const hasScore = c.ai_match_score !== null && c.ai_match_score !== undefined;
    
    if (hasScore) {
      const scoreVal = safeScore(c.ai_match_score);
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: scoreVal >= 70 ? 'var(--success)' : scoreVal >= 45 ? 'var(--warning-dark)' : 'var(--danger)' }}>
            {scoreVal}%
          </span>
          <div style={{ height: 5, background: '#e5e7eb', borderRadius: 999, width: 60, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${scoreVal}%`, background: scoreVal >= 70 ? 'var(--success)' : scoreVal >= 45 ? 'var(--warning)' : 'var(--danger)', borderRadius: 999 }} />
          </div>
        </div>
      );
    }
    
    const verdict = c.ai_verdict;
    if (verdict === "Missing JD" || verdict === "Awaiting JD") {
      return (
        <span style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--text-secondary)' }} title="Please add a description to the job to allow ranking.">
          ⏳ Awaiting JD
        </span>
      );
    }
    
    if (verdict === "Resume parse failed" || verdict === "Embedding generation failed" || verdict === "Extraction confidence too low") {
      return (
        <span 
          style={{ 
            fontSize: 12, 
            fontWeight: 600, 
            color: 'var(--danger-dark)', 
            background: 'var(--danger-light)',
            padding: '4px 8px',
            borderRadius: '4px',
            cursor: 'help',
            border: '1px solid #fee2e2',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px'
          }} 
          title={`Ranking failed: ${verdict}`}
        >
          ⚠️ {verdict}
        </span>
      );
    }

    return (
      <span style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--text-muted)' }}>
        Awaiting ranking
      </span>
    );
  };

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Candidates" />
        <div className="page-body animate-fade">
          <div className="flex-between page-header">
            <div>
              <h1>Candidate Pipeline</h1>
              <p>{candidates.length} candidates found</p>
            </div>
            <div style={{ display:'flex', gap:10 }}>
              <button className="btn btn-secondary btn-sm" style={{ background: 'var(--primary)', color: '#ffffff', borderColor: 'var(--primary)' }} onClick={handleRerankAll}>🔄 Re-rank All</button>
              <button className="btn btn-outline btn-sm" onClick={() => navigate('/compare')}>Compare</button>
              <button className="btn btn-outline btn-sm" onClick={() => downloadReport('csv')}><MdDownload /> CSV</button>
              <button className="btn btn-outline btn-sm" onClick={() => downloadReport('pdf')}><MdDownload /> PDF</button>
              <div style={{ display: 'flex', border: '1px solid #e2e8f0', borderRadius: '6px', overflow: 'hidden' }}>
                <button className={`btn btn-sm ${viewMode === 'list' ? 'btn-primary' : 'btn-ghost'}`} style={{ borderRadius: 0, border: 'none' }} onClick={() => setViewMode('list')} title="List View"><MdViewList size={18} /></button>
                <button className={`btn btn-sm ${viewMode === 'pipeline' ? 'btn-primary' : 'btn-ghost'}`} style={{ borderRadius: 0, border: 'none' }} onClick={() => setViewMode('pipeline')} title="Pipeline View"><MdViewKanban size={18} /></button>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="card" style={{ marginBottom:16 }}>
            <div style={{ display:'flex', gap:12, flexWrap:'wrap', alignItems:'flex-end' }}>
              <form onSubmit={handleSearch} style={{ display:'flex', gap:8, flex:1, minWidth:200 }}>
                <input className="form-input" placeholder="Search name or email…"
                  value={search} onChange={e => setSearch(e.target.value)} style={{ flex:1 }} />
                <button type="submit" className="btn btn-primary"><MdSearch size={18} /> Search</button>
              </form>

              <select className="form-select" style={{ width:160 }} value={jobFilter} onChange={e => setJobFilter(e.target.value)}>
                <option value="">All Jobs</option>
                {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
              </select>

              <select className="form-select" style={{ width:140 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>

              <input className="form-input" placeholder="Location..." style={{ width:120 }}
                value={locationFilter} onChange={e => setLocationFilter(e.target.value)} onBlur={fetchCandidates} />
                
              <input className="form-input" placeholder="Skill (e.g. Python)" style={{ width:140 }}
                value={skillFilter} onChange={e => setSkillFilter(e.target.value)} onBlur={fetchCandidates} />

              <div style={{ display:'flex', alignItems:'center', gap:4 }}>
                <label style={{ fontSize:12, fontWeight:600 }}>Score:</label>
                <input type="number" min={0} max={100} placeholder="Min" className="form-input" style={{ width:70 }}
                  value={minScore} onChange={e => setMinScore(e.target.value)} onBlur={fetchCandidates} />
                <span style={{ fontSize:12 }}>-</span>
                <input type="number" min={0} max={100} placeholder="Max" className="form-input" style={{ width:70 }}
                  value={maxScore} onChange={e => setMaxScore(e.target.value)} onBlur={fetchCandidates} />
              </div>
            </div>
          </div>

          {/* Table or Pipeline */}
          {viewMode === 'list' ? (
          <div className="card" style={{ padding:0, overflow:'hidden' }}>
            <div className="table-wrapper" style={{ border:'none', borderRadius:0 }}>
              {loading ? (
                <div style={{ padding:40, textAlign:'center' }}><div className="spinner" style={{ margin:'0 auto' }} /></div>
              ) : candidates.length === 0 ? (
                <div className="empty-state">
                  <MdFilterList style={{ fontSize:48, color:'var(--text-muted)' }} />
                  <p style={{ marginTop:12 }}>No candidates match your filters.</p>
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--bg-secondary)' }}>
                    <tr>
                      <th style={{ width: '50px', textAlign: 'center' }}>#</th>
                      <th>Candidate Name</th>
                      <th>Email / Contact</th>
                      <th>AI Match</th>
                      <th>AI Verdict</th>
                      <th>Current Stage</th>
                      <th style={{ width: '280px', textAlign: 'right' }}>Recruiter Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c, i) => (
                      <tr key={c.id}>
                        <td style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: 11, fontWeight: 500 }}>{i + 1}</td>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{c.location || 'Remote'}</div>
                        </td>
                        <td>
                          <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{c.email}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>{c.phone || 'No phone'}</div>
                        </td>
                        <td>
                          {renderCandidateScore(c)}
                        </td>
                        <td>
                          {(() => {
                            const hasScore = c.ai_match_score !== null && c.ai_match_score !== undefined;
                            const verdict = c.ai_verdict;

                            if (hasScore && verdict && !["Awaiting JD", "Missing JD", "Resume parse failed", "Embedding generation failed", "Extraction confidence too low"].includes(verdict)) {
                              return (
                                <span className={`badge badge-${verdict.toLowerCase().replace(' ', '-')}`}>
                                  {verdict}
                                </span>
                              );
                            }
                            
                            if (verdict) {
                              return (
                                <span style={{ fontSize: 11.5, color: verdict.includes("failed") || verdict.includes("low") || verdict.includes("Missing") ? 'var(--danger-dark)' : 'var(--text-secondary)', fontStyle: 'italic' }}>
                                  {verdict}
                                </span>
                              );
                            }

                            return (
                              <span style={{ fontSize: 11.5, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                Awaiting ranking
                              </span>
                            );
                          })()}
                        </td>
                        <td>
                          <StatusBadge status={c.status} interview={c.interview} />
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                            <button className="btn btn-outline btn-xs" style={{ fontSize: 11, padding: '3px 8px' }} onClick={() => navigate(`/candidates/${c.id}`)}>
                              Profile
                            </button>
                            <select 
                              className="form-select"
                              value={c.pipeline_stage || c.status || 'applied'} 
                              onChange={(e) => updateStatus(c.id, e.target.value)}
                              style={{ width: '110px', padding: '3px 6px', fontSize: 11, height: '24px', borderRadius: '4px' }}
                            >
                              <option value="applied">Applied</option>
                              <option value="screening">Screening</option>
                              <option value="shortlisted">Shortlist</option>
                              <option value="interview_scheduled">Interview</option>
                              <option value="interview_completed">Completed</option>
                              <option value="offered">Offer</option>
                              <option value="hired">Hired</option>
                              <option value="rejected">Reject</option>
                            </select>
                            {(c.pipeline_stage || c.status) !== 'interview_scheduled' && (c.pipeline_stage || c.status) !== 'interview_completed' && (c.pipeline_stage || c.status) !== 'interview_analyzed' ? (
                              <button className="btn btn-primary btn-xs" style={{ fontSize: 11, padding: '3px 8px', background: 'var(--primary)' }} onClick={() => setInterviewCandidate(c)}>
                                Invite
                              </button>
                            ) : (
                              <button className="btn btn-outline btn-xs" style={{ fontSize: 11, padding: '3px 8px', color: 'var(--primary)', borderColor: 'var(--primary-light)' }} onClick={() => setInterviewCandidate(c)}>
                                Reschedule
                              </button>
                            )}
                            <button 
                              className="btn btn-ghost btn-xs" 
                              style={{ color: 'var(--danger)', padding: '4px', minWidth: 'auto' }} 
                              title="Delete Candidate"
                              onClick={() => {
                                if (window.confirm("Are you sure you want to delete this candidate?")) {
                                  API.delete(`/candidates/${c.id}`).then(() => {
                                    toast.success("Candidate deleted");
                                    fetchCandidates();
                                  }).catch(() => toast.error("Failed to delete candidate"));
                                }
                              }}
                            >
                              <MdDelete size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
          ) : (
            <div style={{ height: 'calc(100vh - 240px)' }}>
              {loading ? (
                <div style={{ padding:40, textAlign:'center' }}><div className="spinner" style={{ margin:'0 auto' }} /></div>
              ) : (
                <KanbanBoard candidates={candidates} onStatusChange={updateStatus} />
              )}
            </div>
          )}
        </div>
      </div>

      {interviewCandidate && (
        <InterviewModal
          candidate={interviewCandidate}
          onClose={() => setInterviewCandidate(null)}
          onSuccess={fetchCandidates}
        />
      )}
    </div>
  );
}
