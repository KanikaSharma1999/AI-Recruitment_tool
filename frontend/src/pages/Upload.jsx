import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import API from '../api/client';
import toast from 'react-hot-toast';
import { MdUpload, MdWork, MdClose, MdCheckCircle } from 'react-icons/md';

export default function Upload() {
  const [jobs, setJobs] = useState([]);
  const [selJob, setSelJob] = useState('');
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [ranking, setRanking] = useState(false);
  const [done, setDone] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showJobForm, setShowJobForm] = useState(false);
  const [jobForm, setJobForm] = useState({ title:'', company:'', description:'', location:'', required_experience_years:0 });
  const navigate = useNavigate();

  useEffect(() => {
    API.get('/jobs/list').then(r => setJobs(r.data)).catch(() => {});
  }, []);

  const setJF = (k, v) => setJobForm(p => ({ ...p, [k]: v }));

  const createJob = async (e) => {
    e.preventDefault();
    try {
      const r = await API.post('/jobs/create', { ...jobForm, required_experience_years: Number(jobForm.required_experience_years) });
      toast.success('Job created!');
      const jobsRes = await API.get('/jobs/list');
      setJobs(jobsRes.data);
      setSelJob(r.data.id);
      setShowJobForm(false);
    } catch { toast.error('Failed to create job'); }
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.match(/\.(pdf|txt)$/i));
    setFiles(prev => [...prev, ...dropped]);
  };

  const removeFile = (i) => setFiles(prev => prev.filter((_, idx) => idx !== i));

  const handleRun = async () => {
    if (!selJob) { toast.error('Select a job first'); return; }
    if (files.length === 0) { toast.error('Upload at least one resume'); return; }

    setUploading(true); setProgress(10);
    try {
      const fd = new FormData();
      fd.append('job_id', selJob);
      files.forEach(f => fd.append('files', f));
      await API.post('/resumes/upload', fd);
      setProgress(50);
      toast.success(`${files.length} resume(s) uploaded`);

      setUploading(false); setRanking(true); setProgress(65);
      const fd2 = new FormData();
      fd2.append('job_id', selJob);
      await API.post('/resumes/rank', fd2);
      setProgress(100);
      setRanking(false); setDone(true);
      toast.success('Ranking complete!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Process failed');
      setUploading(false); setRanking(false);
    }
  };

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Upload Resumes" />
        <div className="page-body animate-fade">
          <div className="page-header">
            <h1>Resume Upload & Ranking</h1>
            <p>Upload resumes to rank candidates against a job description</p>
          </div>

          {done ? (
            <div className="card" style={{ textAlign:'center', padding:60 }}>
              <MdCheckCircle style={{ fontSize:64, color:'var(--success)', marginBottom:16 }} />
              <h2 style={{ marginBottom:8 }}>Ranking Complete!</h2>
              <p style={{ color:'var(--text-secondary)', marginBottom:24 }}>
                {files.length} resumes processed and scored.
              </p>
              <div style={{ display:'flex', gap:12, justifyContent:'center' }}>
                <button className="btn btn-primary" onClick={() => navigate('/candidates')}>
                  View Candidates
                </button>
                <button className="btn btn-outline" onClick={() => { setFiles([]); setDone(false); setProgress(0); }}>
                  Upload More
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
              {/* Job Selection */}
              <div className="card">
                <div className="flex-between" style={{ marginBottom:16 }}>
                  <h3 style={{ fontSize:15, fontWeight:600 }}><MdWork style={{ verticalAlign:'middle', marginRight:6 }} />Select Job</h3>
                  <button className="btn btn-outline btn-sm" onClick={() => setShowJobForm(!showJobForm)}>
                    {showJobForm ? 'Cancel' : '+ Create Job'}
                  </button>
                </div>

                {showJobForm ? (
                  <form onSubmit={createJob} style={{ display:'flex', flexDirection:'column', gap:12 }}>
                    <div className="form-grid">
                      <div className="form-group">
                        <label className="form-label">Job Title *</label>
                        <input className="form-input" required placeholder="e.g. Data Scientist" value={jobForm.title} onChange={e => setJF('title', e.target.value)} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Company *</label>
                        <input className="form-input" required placeholder="Company name" value={jobForm.company} onChange={e => setJF('company', e.target.value)} />
                      </div>
                    </div>
                    <div className="form-grid">
                      <div className="form-group">
                        <label className="form-label">Location</label>
                        <input className="form-input" placeholder="e.g. Remote / Mumbai" value={jobForm.location} onChange={e => setJF('location', e.target.value)} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Required Experience (years)</label>
                        <input type="number" min={0} max={30} className="form-input" value={jobForm.required_experience_years} onChange={e => setJF('required_experience_years', e.target.value)} />
                      </div>
                    </div>
                    <div className="form-group">
                      <label className="form-label">Job Description *</label>
                      <textarea className="form-textarea" required placeholder="Paste full job description here..." rows={5} value={jobForm.description} onChange={e => setJF('description', e.target.value)} />
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ alignSelf:'flex-end' }}>Create Job</button>
                  </form>
                ) : (
                  <select className="form-select" value={selJob} onChange={e => setSelJob(e.target.value)}>
                    <option value="">-- Choose a job posting --</option>
                    {jobs.map(j => <option key={j.id} value={j.id}>{j.title} — {j.company}</option>)}
                  </select>
                )}
              </div>

              {/* Dropzone */}
              <div className="card">
                <h3 style={{ fontSize:15, fontWeight:600, marginBottom:16 }}>
                  <MdUpload style={{ verticalAlign:'middle', marginRight:6 }} />Upload Resumes (PDF / TXT)
                </h3>
                <div
                  className={`dropzone${dragging ? ' active' : ''}`}
                  onDragOver={e => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  onClick={() => document.getElementById('file-input').click()}
                >
                  <MdUpload className="dropzone-icon" />
                  <p style={{ fontWeight:600, marginBottom:6 }}>Drag & drop resumes here</p>
                  <p style={{ fontSize:13, color:'var(--text-secondary)' }}>or click to browse — PDF, TXT supported (100–500 files)</p>
                  <input id="file-input" type="file" multiple accept=".pdf,.txt" style={{ display:'none' }}
                    onChange={e => setFiles(prev => [...prev, ...Array.from(e.target.files)])} />
                </div>

                {files.length > 0 && (
                  <div style={{ marginTop:16 }}>
                    <div className="flex-between" style={{ marginBottom:10 }}>
                      <span style={{ fontSize:13, fontWeight:600 }}>{files.length} file(s) selected</span>
                      <button className="btn btn-outline btn-sm" onClick={() => setFiles([])}>Clear All</button>
                    </div>
                    <div style={{ maxHeight:160, overflowY:'auto', display:'flex', flexDirection:'column', gap:6 }}>
                      {files.map((f, i) => (
                        <div key={i} style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
                          padding:'7px 12px', background:'#f8fafc', borderRadius:6, fontSize:13 }}>
                          <span>{f.name}</span>
                          <button onClick={() => removeFile(i)} style={{ background:'none', border:'none', cursor:'pointer', color:'var(--danger)' }}>
                            <MdClose />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Progress & Run */}
              {(uploading || ranking) && (
                <div className="card">
                  <div style={{ marginBottom:10, fontWeight:600, fontSize:14 }}>
                    {uploading ? 'Uploading and parsing resumes...' : 'Running AI ranking engine...'}
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width:`${progress}%` }} />
                  </div>
                  <div style={{ fontSize:12, color:'var(--text-secondary)', marginTop:6 }}>{progress}% complete</div>
                </div>
              )}

              <button className="btn btn-primary"
                style={{ alignSelf:'flex-start', padding:'12px 28px', fontSize:15 }}
                onClick={handleRun} disabled={uploading || ranking}>
                {uploading || ranking
                  ? <><span className="spinner" /> Processing...</>
                  : 'Upload & Rank Resumes'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
