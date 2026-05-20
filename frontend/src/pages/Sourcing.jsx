import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Navbar from '../components/Navbar';
import API from '../api/client';
import toast from 'react-hot-toast';
import { MdSearch, MdPeople, MdAutoAwesome, MdOpenInNew, MdFilterList } from 'react-icons/md';

export default function Sourcing() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setHasSearched(true);
    try {
      const { data } = await API.get(`/candidates/search?q=${encodeURIComponent(query)}&limit=25`);
      setResults(data);
    } catch (err) {
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="layout">
      <Sidebar />
      <div className="main-content">
        <Navbar title="Talent Database" />
        <div className="page-body animate-fade">
          
          <div className="flex-between page-header" style={{ marginBottom: 24 }}>
            <div>
              <h1 style={{ fontSize: 24, fontWeight: 800, color: '#1e293b' }}>Global Talent Database</h1>
              <p style={{ color: '#64748b', fontSize: 14 }}>Semantic AI search across all resumes in your ATS</p>
            </div>
          </div>

          <div className="card" style={{ padding: 24, marginBottom: 24, background: 'linear-gradient(to right, #ffffff, #f8fafc)', border: '1px solid #e2e8f0' }}>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <MdSearch style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', fontSize: 22, color: '#94a3b8' }} />
                <input 
                  type="text" 
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder='Try "Senior React developer with AWS experience" or "Data Scientist with NLP projects"'
                  className="form-input"
                  style={{ width: '100%', padding: '16px 16px 16px 48px', fontSize: 15, borderRadius: 12, border: '1px solid #cbd5e1', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ padding: '16px 32px', borderRadius: 12, fontSize: 15 }} disabled={loading || !query.trim()}>
                {loading ? <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} /> : <><MdAutoAwesome /> Search</>}
              </button>
            </form>
            
            <div style={{ display: 'flex', gap: 12, marginTop: 16, alignItems: 'center' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: '#64748b' }}>SUGGESTED:</span>
              {['Frontend React', 'Python Machine Learning', 'Senior DevOps AWS'].map(s => (
                <button 
                  key={s} 
                  type="button"
                  onClick={() => { setQuery(s); setTimeout(() => handleSearch(), 0); }}
                  style={{ background: '#f1f5f9', border: 'none', padding: '6px 12px', borderRadius: 20, fontSize: 12, color: '#475569', cursor: 'pointer', fontWeight: 500 }}
                  className="hover-lift"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {!hasSearched ? (
             <div style={{ padding: '80px 20px', textAlign: 'center', background: '#fff', borderRadius: 16, border: '1px dashed #cbd5e1' }}>
               <div style={{ width: 64, height: 64, background: '#f8fafc', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
                 <MdPeople size={32} color="#94a3b8" />
               </div>
               <h3 style={{ fontSize: 18, fontWeight: 700, color: '#334155', marginBottom: 8 }}>Search your entire talent pool</h3>
               <p style={{ color: '#64748b', maxWidth: 400, margin: '0 auto', fontSize: 14, lineHeight: 1.6 }}>
                 Enter skills, roles, or natural language descriptions. The AI will instantly search across all resumes, even those in past pipelines.
               </p>
             </div>
          ) : loading ? (
             <div style={{ padding: 60, textAlign: 'center' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
          ) : results.length === 0 ? (
             <div className="empty-state">
               <MdFilterList style={{ fontSize:48, color:'#94a3b8' }} />
               <p style={{ marginTop:12 }}>No talent found matching your search. Try different keywords.</p>
             </div>
          ) : (
            <div className="card" style={{ padding: 0 }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#475569' }}>{results.length} Candidates Found</span>
                <span style={{ fontSize: 12, color: '#64748b' }}>Ranked by Semantic AI Relevance</span>
              </div>
              <div className="table-responsive">
                <table className="table" style={{ fontSize: 14 }}>
                  <thead>
                    <tr>
                      <th style={{ color: '#64748b', fontWeight: 600 }}>CANDIDATE</th>
                      <th style={{ color: '#64748b', fontWeight: 600 }}>MATCH RELEVANCE</th>
                      <th style={{ color: '#64748b', fontWeight: 600 }}>EXPERIENCE</th>
                      <th style={{ color: '#64748b', fontWeight: 600 }}>ORIGINAL PIPELINE</th>
                      <th style={{ color: '#64748b', fontWeight: 600 }}>ACTION</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((c) => (
                      <tr key={c.id}>
                        <td>
                          <div style={{ fontWeight: 700, color: '#1e293b' }}>{c.name}</div>
                          <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>{c.email}</div>
                          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                            {c.skills?.slice(0, 3).map(s => (
                              <span key={s} style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>{s}</span>
                            ))}
                            {c.skills?.length > 3 && <span style={{ background: '#f1f5f9', padding: '2px 6px', borderRadius: 4 }}>+{c.skills.length - 3}</span>}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#ede9fe', color: '#6366f1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 12 }}>
                              {Math.round(c.semantic_similarity * 100)}%
                            </div>
                            <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>Semantic Fit</span>
                          </div>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: '#334155' }}>{c.experience_years} years</div>
                        </td>
                        <td>
                          <div style={{ fontSize: 13, color: '#334155', fontWeight: 500 }}>{c.original_job_title || 'Unknown Role'}</div>
                          <div style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', marginTop: 2 }}>
                            {c.status?.replace('_', ' ')}
                          </div>
                        </td>
                        <td>
                          <button 
                            className="btn btn-outline btn-sm" 
                            style={{ borderRadius: 8 }}
                            onClick={() => window.open(`/candidates/${c.id}`, '_blank')}
                          >
                            <MdOpenInNew /> Profile
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
