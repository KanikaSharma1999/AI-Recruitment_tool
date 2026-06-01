import React, { useState } from 'react';
import API from '../api/client';
import { MdQuestionAnswer, MdAutoAwesome, MdRefresh, MdContentCopy } from 'react-icons/md';
import { toast } from 'react-hot-toast';

export default function InterviewPrepCard({ candidateId, jobId, jobTitle }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [generatedBy, setGeneratedBy] = useState(null);

  const generateQuestions = async () => {
    setLoading(true);
    try {
      const res = await API.post('/interviews/generate-questions', {
        job_id: jobId,
        candidate_id: candidateId
      });
      setQuestions(res.data.questions || []);
      setGeneratedBy(res.data.generated_by);
      toast.success('Interview questions generated!');
    } catch (err) {
      console.error(err);
      toast.error('Failed to generate questions');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="card" style={{ marginTop: 20 }}>
      <div className="flex-between" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #8b5cf6, #d946ef)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
            <MdQuestionAnswer size={18} />
          </div>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>AI Interview Preparation</h3>
        </div>
        <button 
          className="btn btn-primary btn-sm" 
          onClick={generateQuestions}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          {loading ? <div className="spinner-xs" /> : <MdAutoAwesome />}
          {questions.length > 0 ? 'Regenerate' : 'Generate Questions'}
        </button>
      </div>

      {questions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--text-muted)' }}>
          <p style={{ fontSize: 13, marginBottom: 12 }}>
            Generate personalized interview questions based on this candidate's skill gaps and the job requirements.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Suggested Questions ({questions.length})
            </span>
            <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: generatedBy === 'cohere' ? '#ede9fe' : '#f3f4f6', color: generatedBy === 'cohere' ? '#7c3aed' : '#6b7280', fontWeight: 700 }}>
              {generatedBy === 'cohere' ? 'AI GENERATED' : 'TEMPLATE BASED'}
            </span>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {questions.map((q, i) => (
              <div key={i} style={{ padding: '12px 14px', borderRadius: 10, background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', position: 'relative', group: 'true' }} className="question-item">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 800, color: q.type === 'Technical' ? '#3b82f6' : '#10b981', textTransform: 'uppercase' }}>
                    {q.type}
                  </span>
                  <button 
                    onClick={() => copyToClipboard(q.question)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
                    title="Copy question"
                  >
                    <MdContentCopy size={14} />
                  </button>
                </div>
                <p style={{ fontSize: 13.5, color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>
                  {q.question}
                </p>
              </div>
            ))}
          </div>
          
          <div style={{ marginTop: 8, padding: '10px 12px', borderRadius: 8, background: '#eff6ff', border: '1px solid #bfdbfe', display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ color: '#3b82f6' }}><MdAutoAwesome size={18} /></div>
            <p style={{ fontSize: 12, color: '#1e40af', margin: 0 }}>
              <strong>Recruiter Tip:</strong> These questions target {candidateId ? "this candidate's specific missing skills" : "the core job requirements"} to verify technical depth.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
