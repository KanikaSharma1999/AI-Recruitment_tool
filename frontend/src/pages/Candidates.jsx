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
  { value: 'interviewed', label: 'Interviewed' },
  { value: 'selected', label: 'Selected' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'on_hold', label: 'On Hold' }
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
              <button className="btn btn-outline btn-sm" onClick={() => navigate('/compare')}>⚖ Compare</button>
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
                <button type="submit" className="btn btn-primary btn-sm"><MdSearch /></button>
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
                <input type="number" min={0} max={100} placeholder="Min" className="form-input" style={{ width:60, padding:'6px' }}
                  value={minScore} onChange={e => setMinScore(e.target.value)} onBlur={fetchCandidates} />
                <span style={{ fontSize:12 }}>-</span>
                <input type="number" min={0} max={100} placeholder="Max" className="form-input" style={{ width:60, padding:'6px' }}
                  value={maxScore} onChange={e => setMaxScore(e.target.value)} onBlur={fetchCandidates} />
              </div>
            </div>
          </div>

          {/* Table or Pipeline */}
          {viewMode === 'list' ? (
          <div className="card" style={{ padding:0 }}>
            <div className="table-wrapper">
              {loading ? (
                <div style={{ padding:40, textAlign:'center' }}><div className="spinner" style={{ margin:'0 auto' }} /></div>
              ) : candidates.length === 0 ? (
                <div className="empty-state">
                  <MdFilterList style={{ fontSize:48, color:'#94a3b8' }} />
                  <p style={{ marginTop:12 }}>No candidates match your filters.</p>
                </div>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>#</th><th>Name</th><th>Email</th><th>AI Score</th>
                      <th>Recommendation</th><th>Status</th><th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c, i) => (
                      <tr key={c.id}>
                        <td style={{ color:'var(--text-secondary)', fontSize:12 }}>{i + 1}</td>
                        <td style={{ fontWeight:600 }}>{c.name}</td>
                        <td style={{ fontSize:12, color:'var(--text-secondary)' }}>{c.email}</td>
                        <td>
                          <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
                            <span style={{ fontSize:18, fontWeight:800, color: safeScore(c.score)>=70?'#059669':safeScore(c.score)>=45?'#d97706':'#dc2626' }}>
                              {safeScore(c.score)}%
                            </span>
                            <div style={{ height:4, background:'#e5e7eb', borderRadius:999, width:72, overflow:'hidden' }}>
                              <div style={{ height:'100%', width:`${safeScore(c.score)}%`, background: safeScore(c.score)>=70?'#10b981':safeScore(c.score)>=45?'#f59e0b':'#ef4444', borderRadius:999 }} />
                            </div>
                          </div>
                        </td>
                        <td>
                          {c.hiring_summary?.recommendation ? (
                            <span style={{
                              padding:'3px 10px', borderRadius:999, fontSize:11, fontWeight:700,
                              background: {'Strong Hire':'#d1fae5','Hire':'#dbeafe','Hold':'#fef3c7','Reject':'#fee2e2'}[c.hiring_summary.recommendation]||'#f3f4f6',
                              color: {'Strong Hire':'#065f46','Hire':'#1e40af','Hold':'#92400e','Reject':'#991b1b'}[c.hiring_summary.recommendation]||'#6b7280',
                            }}>
                              {c.hiring_summary.recommendation}
                            </span>
                          ) : (
                            <span style={{ fontSize:12, color:'var(--text-muted)' }}>Not ranked</span>
                          )}
                        </td>
                        <td><StatusBadge status={c.status} /></td>
                        <td>
                          <div className="actions-cell">
                            <button className="btn btn-outline btn-sm" title="Pending"
                              onClick={() => updateStatus(c.id, 'pending')}>P</button>
                            <button className="btn btn-success btn-sm" title="Shortlist"
                              onClick={() => updateStatus(c.id, 'shortlisted')}><MdThumbUp /></button>
                            <button className="btn btn-danger btn-sm" title="Reject"
                              onClick={() => updateStatus(c.id, 'rejected')}><MdThumbDown /></button>
                            <button className="btn btn-info btn-sm" title="Schedule Interview"
                              onClick={() => setInterviewCandidate(c)}><MdCalendarToday /></button>
                            <button className="btn btn-purple btn-sm" title="Select"
                              onClick={() => updateStatus(c.id, 'selected')}><MdCheckCircle /></button>
                            <button className="btn btn-outline btn-sm" title="View Profile"
                              onClick={() => navigate(`/candidates/${c.id}`)}><MdVisibility /></button>
                            <button className="btn btn-outline btn-sm" title="Delete" style={{ borderColor:'var(--danger)', color:'var(--danger)' }}
                              onClick={() => {
                                if (window.confirm("Are you sure you want to delete this candidate?")) {
                                  API.delete(`/candidates/${c.id}`).then(() => {
                                    toast.success("Candidate deleted");
                                    fetchCandidates();
                                  }).catch(() => toast.error("Failed to delete candidate"));
                                }
                              }}><MdDelete /></button>
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
